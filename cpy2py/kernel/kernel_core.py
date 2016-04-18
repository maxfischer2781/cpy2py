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
"""
The kernel is the main thread of execution running inside a twinterpreter.

Any connection between twinterpreters is handled by two kernels. Each
consists of client and server side residing in the different interpreters.

The kernels assume that they have been setup properly. Use
:py:class:`~cpy2py.twinterpreter.twin_master.TwinMaster` start kernel pairs.
"""
import sys
import os
import time
import logging

from cpy2py.utility.compat import pickle
from cpy2py.kernel import kernel_state

from cpy2py.utility.exceptions import format_exception, CPy2PyException
from cpy2py.ipyc import ipyc_exceptions
from cpy2py.kernel.kernel_exceptions import TwinterpeterTerminated
from cpy2py.proxy import proxy_tracker

# Message Enums
# twin call type
__E_SHUTDOWN__ = -1
__E_CALL_FUNC__ = 11
__E_CALL_METHOD__ = 12
__E_GET_ATTRIBUTE__ = 21
__E_SET_ATTRIBUTE__ = 22
__E_DEL_ATTRIBUTE__ = 23
__E_INSTANTIATE__ = 31
__E_REF_INCR__ = 32
__E_REF_DECR__ = 33
# twin reply type
__E_SUCCESS__ = 101
__E_EXCEPTION__ = 102

E_SYMBOL = {
    __E_SHUTDOWN__: '__E_SHUTDOWN__',
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


class StopTwinterpreter(CPy2PyException):
    """Signal to stop the twinterpeter"""
    def __init__(self, message="Twinterpreter Shutdown", exit_code=1):
        CPy2PyException.__init__(self, message)
        self.exit_code = exit_code


class SingleThreadKernelServer(object):
    """
    Default kernel server for sending requests to other interpreter

    :param peer_id: id of the kernel/twinterpreter this kernel is peered with
    :type peer_id: str
    :param ipyc: :py:mod:`~IPyC` for incoming requests
    :type ipyc: :py:class:`~DuplexFifoIPyC`
    :param pickle_protocol: protocol number for :py:mod:`pickle`
    :type pickle_protocol: int
    """
    def __new__(cls, peer_id, *args, **kwargs):  # pylint: disable=unused-argument
        assert peer_id not in kernel_state.KERNEL_SERVERS, 'Twinterpreters must have unique IDs'
        kernel_state.KERNEL_SERVERS[peer_id] = object.__new__(cls)
        return kernel_state.KERNEL_SERVERS[peer_id]

    def __init__(self, peer_id, ipyc, pickle_protocol=2):
        self._logger = logging.getLogger('__cpy2py__.%s' % kernel_state.TWIN_ID)
        self.peer_id = peer_id
        self._ipyc = ipyc
        self._ipyc.open()
        self._server_send, self._server_recv = _connect_ipyc(ipyc, pickle_protocol)
        # instance => ref_count
        self._instances_keepalive = {}
        # directive lookup for methods
        self._directive_method = {
            __E_SHUTDOWN__: self._directive_shutdown,
            __E_CALL_FUNC__: self._directive_call_func,
            __E_CALL_METHOD__: self._directive_call_method,
            __E_GET_ATTRIBUTE__: self._directive_get_attribute,
            __E_SET_ATTRIBUTE__: self._directive_set_attribute,
            __E_DEL_ATTRIBUTE__: self._directive_del_attribute,
            __E_INSTANTIATE__: self._directive_instantiate,
            __E_REF_INCR__: self._directive_ref_incr,
            __E_REF_DECR__: self._directive_ref_decr,
        }

    def run(self):
        """
        Run the kernel request server

        :returns: exit code indicating potential failure
        """
        exit_code, request_id = 1, None
        self._logger.warning('Starting kernel %s @ %s', kernel_state.TWIN_ID, time.asctime())
        try:
            while True:
                self._logger.warning('Listening [%s]', kernel_state.TWIN_ID)
                request_id, directive = self._server_recv()
                self._serve_request(request_id, directive)
        except StopTwinterpreter as err:
            self._server_send((request_id, __E_SHUTDOWN__, err.exit_code))
            exit_code = err.exit_code
        # cPickle may raise EOFError by itself
        except (ipyc_exceptions.IPyCTerminated, EOFError):
            exit_code = 0
        except Exception as err:  # pylint: disable=broad-except
            self._logger.critical('TWIN KERNEL INTERNAL EXCEPTION')
            format_exception(self._logger, 3)
            self._server_send((request_id, __E_EXCEPTION__, err))
        finally:
            self._logger.critical('TWIN KERNEL SHUTDOWN: %s => %d', kernel_state.TWIN_ID, exit_code)
            self._ipyc.close()
            del kernel_state.KERNEL_SERVERS[self.peer_id]
        return exit_code

    def _serve_request(self, request_id, directive):
        """Serve a request from :py:meth:`_dispatch_request`"""
        try:
            directive_type, directive_body = directive
            directive_symbol = E_SYMBOL[directive_type]
            directive_method = self._directive_method[directive_type]
        except (KeyError, ValueError) as err:
            # error in lookup or unpacking
            raise CPy2PyException(err)
        try:
            self._logger.warning('Directive %s', directive_symbol)
            response = directive_method(directive_body)
        # catch internal errors to reraise them
        except CPy2PyException:
            raise
        # send everything else back to calling scope
        except Exception as err:  # pylint: disable=broad-except
            self._server_send((request_id, __E_EXCEPTION__, err))
            self._logger.critical('TWIN KERNEL PAYLOAD EXCEPTION')
            format_exception(self._logger, 3)
            if isinstance(err, (KeyboardInterrupt, SystemExit)):
                raise StopTwinterpreter(message=err.__class__.__name__, exit_code=1)
        else:
            self._server_send((request_id, __E_SUCCESS__, response))

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

    @staticmethod
    def _directive_shutdown(directive_body):
        """Directive for :py:meth:`stop`"""
        message = directive_body[0]
        raise StopTwinterpreter(message=message, exit_code=0)

    def __repr__(self):
        return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())


def _connect_ipyc(ipyc, pickle_protocol):
    """Connect pickle/unpickle trackers to a duplyed IPyC"""
    pickler = pickle.Pickler(ipyc.writer, pickle_protocol)
    pickler.persistent_id = proxy_tracker.persistent_twin_id
    send = pickler.dump
    unpickler = pickle.Unpickler(ipyc.reader)
    unpickler.persistent_load = proxy_tracker.persistent_twin_load
    recv = unpickler.load
    return send, recv


class SingleThreadKernelClient(object):
    """
    Default kernel client for sending requests to other interpreter

    :param peer_id: id of the kernel/twinterpreter this kernel is peered with
    :type peer_id: str
    :param ipyc: :py:mod:`~IPyC` for outgoing requests
    :type ipyc: :py:class:`~DuplexFifoIPyC`
    :param pickle_protocol: protocol number for :py:mod:`pickle`
    :type pickle_protocol: int
    """
    def __new__(cls, peer_id, *args, **kwargs):  # pylint: disable=unused-argument
        assert peer_id not in kernel_state.KERNEL_CLIENTS, 'Twinterpreters must have unique IDs'
        kernel_state.KERNEL_CLIENTS[peer_id] = object.__new__(cls)
        return kernel_state.KERNEL_CLIENTS[peer_id]

    def __init__(self, peer_id, ipyc, pickle_protocol=2):
        self._logger = logging.getLogger('__cpy2py__.%s' % kernel_state.TWIN_ID)
        self.peer_id = peer_id
        # communication
        self._ipyc = ipyc
        self._ipyc.open()
        self._client_send, self._client_recv = _connect_ipyc(ipyc, pickle_protocol)
        self._request_id = 0

    # dispatching: execute actions in other interpeter
    def _dispatch_request(self, request_type, *args):
        """Forward a request to peer and return result"""
        self._request_id += 1
        my_id = self._request_id
        try:
            self._client_send((my_id, (request_type, args)))
            request_id, result_type, result_body = self._client_recv()
        except ipyc_exceptions.IPyCTerminated:
            raise TwinterpeterTerminated(twin_id=self.peer_id)
        assert request_id == my_id, 'kernel messages order'
        if result_type == __E_SUCCESS__:
            return result_body
        elif result_type == __E_EXCEPTION__:
            raise result_body
        elif result_type == __E_SHUTDOWN__:
            return True
        raise RuntimeError

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

    def stop(self):
        """Shutdown the peer's server"""
        if self._dispatch_request(__E_SHUTDOWN__, 'stop'):
            self._ipyc.close()
            del kernel_state.KERNEL_CLIENTS[self.peer_id]
            return True
        return False

    def __repr__(self):
        return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())
