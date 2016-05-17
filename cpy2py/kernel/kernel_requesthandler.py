# - # Copyright 2016 Max Fischer
# - #
# - # Licensed under the Apache License, Version 2.0 (the "License");
# - # you may not use this file except in compliance with the License.
# - # You may obtain a copy of the License at
# - #
# - #     http://www.apache.org/licenses/LICENSE-2.0
# - #
# - # Unless required by applicable law or agreed to in writing, software
# - # distributed under the License is distributed on an "AS IS" BASIS,
# - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# - # See the License for the specific language governing permissions and
# - # limitations under the License.
import logging

from cpy2py.kernel import kernel_state
from cpy2py.ipyc import ipyc_exceptions
from cpy2py.utility.exceptions import format_exception, CPy2PyException
from cpy2py.kernel.kernel_exceptions import StopTwinterpreter, TwinterpeterTerminated


# Message Enums
# twin call type
# # calls
__E_CALL_FUNC__ = 11
__E_CALL_METHOD__ = 12
# # attributes
__E_GET_ATTRIBUTE__ = 21
__E_SET_ATTRIBUTE__ = 22
__E_DEL_ATTRIBUTE__ = 23
# instantiation/references
__E_INSTANTIATE__ = 31
__E_REF_INCR__ = 32
__E_REF_DECR__ = 33
# twin reply type
__E_SUCCESS__ = 101
__E_EXCEPTION__ = 102

E_SYMBOL = {
    __E_CALL_FUNC__: '__E_CALL_FUNC__',
    __E_CALL_METHOD__: '__E_CALL_METHOD__',
    __E_GET_ATTRIBUTE__: '__E_GET_ATTRIBUTE__',
    __E_SET_ATTRIBUTE__: '__E_SET_ATTRIBUTE__',
    __E_DEL_ATTRIBUTE__: '__E_DEL_ATTRIBUTE__',
    __E_INSTANTIATE__: '__E_INSTANTIATE__',
    __E_REF_INCR__: '__E_REF_INCR__',
    __E_REF_DECR__: '__E_REF_DECR__',
    __E_SUCCESS__: '__E_SUCCESS__',
    __E_EXCEPTION__: '__E_EXCEPTION__',
}


class TerminationEvent(object):
    def __init__(self, message='shutdown', exit_code=0):
        self.message = message
        self.exit_code = exit_code

    @staticmethod
    def __setstate__(state):
        raise StopTwinterpreter(message=state['message'], exit_code=state['exit_code'])


class RequestHandler(object):
    """
    Handler for requests between kernels

    :param peer_id: id of the kernel/twinterpreter this handler serves
    :type peer_id: str
    :param kernel_server: server receiving requests and sending replies
    :type kernel_server: :py:class:`~cpy2py.kernel.kernel_single.SingleThreadKernelServer`
    """
    def __init__(self, peer_id, kernel_server):
        self._logger = logging.getLogger('__cpy2py__.kernel.%s_to_%s.handler' % (kernel_state.TWIN_ID, peer_id))
        self.peer_id = peer_id
        self.kernel_server = kernel_server
        # instance => ref_count
        self._instances_keepalive = {}
        # directive lookup for methods
        self._directive_method = {
            __E_CALL_FUNC__: self._directive_call_func,
            __E_CALL_METHOD__: self._directive_call_method,
            __E_GET_ATTRIBUTE__: self._directive_get_attribute,
            __E_SET_ATTRIBUTE__: self._directive_set_attribute,
            __E_DEL_ATTRIBUTE__: self._directive_del_attribute,
            __E_INSTANTIATE__: self._directive_instantiate,
            __E_REF_INCR__: self._directive_ref_incr,
            __E_REF_DECR__: self._directive_ref_decr,
        }

    def serve_request(self, request_id, directive):
        """Serve a request from :py:meth:`_dispatch_request`"""
        # unpack request
        try:
            directive_type, directive_body = directive
            directive_method = self._directive_method[directive_type]
        except (KeyError, ValueError) as err:
            # error in lookup or unpacking
            raise CPy2PyException(err)
        # run request
        try:
            if __debug__:
                self._logger.warning('<%s> [%s] Directive %s', kernel_state.TWIN_ID, self.peer_id, E_SYMBOL[directive_type])
            response = directive_method(directive_body)
        # catch internal errors to reraise them
        except CPy2PyException:
            raise
        # send everything else back to calling scope
        except Exception as err:  # pylint: disable=broad-except
            self.kernel_server.send_reply(request_id, (__E_EXCEPTION__, err))
            self._logger.critical('<%s> [%s] TWIN KERNEL PAYLOAD EXCEPTION', kernel_state.TWIN_ID, self.peer_id)
            format_exception(self._logger, 3)
            if isinstance(err, (KeyboardInterrupt, SystemExit)):
                raise StopTwinterpreter(message=err.__class__.__name__, exit_code=1)
        else:
            self.kernel_server.send_reply(request_id, (__E_SUCCESS__, response))

    @staticmethod
    def _directive_call_func(directive_body):
        """Directive for :py:meth:`dispatch_call`"""
        func_obj, func_args, func_kwargs = directive_body
        return func_obj(*func_args, **func_kwargs)

    @staticmethod
    def _directive_call_method(directive_body):
        """Directive for :py:meth:`dispatch_method_call`"""
        instance, method_name, method_args, method_kwargs = directive_body
        return getattr(instance, method_name)(*method_args, **method_kwargs)

    @staticmethod
    def _directive_get_attribute(directive_body):
        """Directive for :py:meth:`get_attribute`"""
        instance, attribute_name = directive_body
        return getattr(instance, attribute_name)

    @staticmethod
    def _directive_set_attribute(directive_body):
        """Directive for :py:meth:`set_attribute`"""
        instance, attribute_name, new_value = directive_body
        return setattr(instance, attribute_name, new_value)

    @staticmethod
    def _directive_del_attribute(directive_body):
        """Directive for :py:meth:`del_attribute`"""
        instance, attribute_name = directive_body
        return delattr(instance, attribute_name)

    def _directive_instantiate(self, directive_body):
        """Directive for :py:meth:`instantiate_class`"""
        cls, cls_args, cls_kwargs = directive_body
        instance = cls(*cls_args, **cls_kwargs)
        self._instances_keepalive[instance] = 1
        return instance.__instance_id__

    def _directive_ref_incr(self, directive_body):
        """Directive for :py:meth:`increment_instance_ref`"""
        instance = directive_body[0]
        try:
            self._instances_keepalive[instance] += 1
        except KeyError:
            self._instances_keepalive[instance] = 1
        return self._instances_keepalive[instance]

    def _directive_ref_decr(self, directive_body):
        """Directive for :py:meth:`decrement_instance_ref`"""
        instance = directive_body[0]
        self._instances_keepalive[instance] -= 1
        response = self._instances_keepalive[instance]
        if self._instances_keepalive[instance] <= 0:
            del self._instances_keepalive[instance]
        return response

    def __repr__(self):
        return '<%s[%s]>' % (self.__class__.__name__, self.kernel_server)


class RequestDispatcher(object):
    """
    Dispatcher for requests between kernels

    The :py:class:`~.RequestDispatcher` is the only part of a kernel
    that non-kernel elements should interact with. It encapsulates the
    encoding, sending, receiving and decoding of requests.

    Since it is tightly interwoven with the rest of the kernel, this
    class should not be instantiated manually. Use
    :py:func:`~cpy2py.kernel.kernel_state.get_kernel` to receive an
    active dispatcher. Instances of this class are automatically
    created when a kernel boots. See
    :py:class:`~cpy2py.twinterpreter.twin_master.TwinMaster` for
    details on this.

    :param peer_id: id of the kernel/twinterpreter this handler serves
    :type peer_id: str
    :param kernel_client: client sending requests and receiving replies
    :type kernel_client: :py:class:`~cpy2py.kernel.kernel_single.SingleThreadKernelClient`
    """
    #: placeholder for replies that have not been served
    empty_reply = (None, None)

    def __init__(self, peer_id, kernel_client):
        self._logger = logging.getLogger('__cpy2py__.kernel.%s_to_%s.dispatcher' % (kernel_state.TWIN_ID, peer_id))
        self.peer_id = peer_id
        self.kernel_client = kernel_client
        self.exit_code = None

    def _dispatch_request(self, request_type, *args):
        """Forward a request to peer and return the result"""
        try:
            result_type, result_body = self.kernel_client.run_request((request_type, args))
        except (ipyc_exceptions.IPyCTerminated, IOError, ValueError):
            raise TwinterpeterTerminated(twin_id=self.peer_id)
        if result_type == __E_SUCCESS__:
            return result_body
        elif result_type == __E_EXCEPTION__:
            raise result_body
        elif result_type is None:
            raise TwinterpeterTerminated(twin_id=self.peer_id)
        raise RuntimeError

    def _dispatch_event(self, request_type, *args):
        """Forward a request to peer and return the result"""
        try:
            self.kernel_client.run_event((request_type, args))
        except (ipyc_exceptions.IPyCTerminated, IOError, ValueError):
            raise TwinterpeterTerminated(twin_id=self.peer_id)
        return True

    def dispatch_call(self, call, *call_args, **call_kwargs):
        """Execute a function call and return the result"""
        return self._dispatch_request(__E_CALL_FUNC__, call, call_args, call_kwargs)

    def dispatch_method_call(self, instance, method_name, *method_args, **methods_kwargs):
        """Execute a method call and return the result"""
        return self._dispatch_request(__E_CALL_METHOD__, instance, method_name, method_args, methods_kwargs)

    def get_attribute(self, instance, attribute_name):
        """Get an attribute of an instance"""
        return self._dispatch_request(__E_GET_ATTRIBUTE__, instance, attribute_name)

    def set_attribute(self, instance, attribute_name, new_value):
        """Set an attribute of an instance"""
        return self._dispatch_request(__E_SET_ATTRIBUTE__, instance, attribute_name, new_value)

    def del_attribute(self, instance, attribute_name):
        """Delete an attribute of an instance"""
        return self._dispatch_request(__E_DEL_ATTRIBUTE__, instance, attribute_name)

    def instantiate_class(self, cls, *cls_args, **cls_kwargs):
        """Instantiate a class, increment its reference count, and return its id"""
        return self._dispatch_request(__E_INSTANTIATE__, cls, cls_args, cls_kwargs)

    def increment_instance_ref(self, instance):
        """Increment the reference count to an instance by one"""
        return self._dispatch_request(__E_REF_INCR__, instance)

    def decrement_instance_ref(self, instance):
        """Decrement the reference count to an instance by one"""
        return self._dispatch_request(__E_REF_DECR__, instance)

    def shutdown_peer(self, message='shutdown'):
        """Tell peer to shut down"""
        try:
            return self._dispatch_event(TerminationEvent(message=message, exit_code=0))
        except TwinterpeterTerminated:
            return True

    def stop(self):
        return self.kernel_client.stop()

