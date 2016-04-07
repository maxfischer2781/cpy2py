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
"""
import sys
import os
import time
import logging
import weakref

from cpy2py.utility.compat import pickle
from cpy2py.twinterpreter import kernel_state

from cpy2py.utility.exceptions import format_exception, CPy2PyException
from cpy2py.ipyc import ipyc_exceptions
from cpy2py.twinterpreter.kernel_exceptions import TwinterpeterTerminated
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


class InstanceLookupError(CPy2PyException):
    """Lookup of an instance failed"""
    def __init__(self, instance_id):
        CPy2PyException.__init__(self, 'Lookup of instance %s failed' % instance_id)
        self.instance_id = instance_id


class SingleThreadKernel(object):
    """
    Default kernel for handling requests between interpeters

    Any connection between twinterpreters is handled by two kernels, one in each
    twinterpreter. In each twinterpreter, the local kernel provides a client
    interface for dispatching calls. At the same time, it acts as a server that
    handles requests from its peer.

    The kernels assume that they have been setup properly. Use
    :py:class:`~TwinMaster` start kernel peers.

    :param peer_id: id of the kernel/twinterpreter this kernel is peered with
    :type peer_id: str
    :param server_ipyc: :py:mod:`~IPyC` for incoming requests
    :type server_ipyc: :py:class:`~DuplexFifoIPyC`
    :param client_ipyc: :py:mod:`~IPyC` for outgoing requests
    :type client_ipyc: :py:class:`~DuplexFifoIPyC`
    """
    def __new__(cls, peer_id, *args, **kwargs):  # pylint: disable=unused-argument
        assert peer_id not in kernel_state.KERNELS, 'Twinterpreters must have unique IDs'
        kernel_state.KERNELS[peer_id] = object.__new__(cls)
        return kernel_state.KERNELS[peer_id]

    def __init__(self, peer_id, server_ipyc, client_ipyc, pickle_protocol=2):
        self._logger = logging.getLogger('__cpy2py__.%s' % kernel_state.TWIN_ID)
        self.peer_id = peer_id
        self._ipyc = (server_ipyc, client_ipyc)
        if kernel_state.is_twinterpreter(kernel_state.MASTER_ID):
            server_ipyc.open()
            client_ipyc.open()
        else:
            client_ipyc.open()
            server_ipyc.open()
        # communication
        self._server_send, self._server_recv = self._connect_ipyc(server_ipyc, pickle_protocol)
        self._client_send, self._client_recv = self._connect_ipyc(client_ipyc, pickle_protocol)
        self._request_id = 0
        # instance_id => [ref_count, instance]
        self._instances_keepalive = {}
        # instance_id => instance
        self._instances_alive_ref = weakref.WeakValueDictionary()
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

    @staticmethod
    def _connect_ipyc(ipyc, pickle_protocol):
        """Connect to an IPyC duplex"""
        pickler = pickle.Pickler(ipyc.writer, pickle_protocol)
        pickler.persistent_id = proxy_tracker.persistent_twin_id
        send = pickler.dump
        unpickler = pickle.Unpickler(ipyc.reader)
        unpickler.persistent_load = proxy_tracker.persistent_twin_load
        recv = unpickler.load
        return send, recv

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
        except Exception:  # pylint: disable=broad-except
            self._logger.critical('TWIN KERNEL INTERNAL EXCEPTION')
            format_exception(self._logger, 3)
        finally:
            self._logger.critical('TWIN KERNEL SHUTDOWN: %s => %d', kernel_state.TWIN_ID, exit_code)
            for ipyc in self._ipyc:
                ipyc.close()
            del kernel_state.KERNELS[self.peer_id]
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

    @staticmethod
    def _directive_call_func(directive_body):
        """Directive for :py:meth:`dispatch_call`"""
        func_obj, func_args, func_kwargs = directive_body
        return func_obj(*func_args, **func_kwargs)

    def dispatch_method_call(self, instance_id, method_name, *method_args, **methods_kwargs):
        """Execute a method call and return the result"""
        return self._dispatch_request(__E_CALL_METHOD__, instance_id, method_name, method_args, methods_kwargs)

    def _directive_call_method(self, directive_body):
        """Directive for :py:meth:`dispatch_method_call`"""
        inst_id, method_name, method_args, method_kwargs = directive_body
        try:
            instance = self._instances_alive_ref[inst_id]
        except KeyError:
            raise InstanceLookupError(instance_id=inst_id)
        return getattr(instance, method_name)(*method_args, **method_kwargs)

    def get_attribute(self, instance_id, attribute_name):
        """Get an attribute of an instance"""
        return self._dispatch_request(__E_GET_ATTRIBUTE__, instance_id, attribute_name)

    def _directive_get_attribute(self, directive_body):
        """Directive for :py:meth:`get_attribute`"""
        inst_id, attribute_name = directive_body
        try:
            instance = self._instances_alive_ref[inst_id]
        except KeyError:
            raise InstanceLookupError(instance_id=inst_id)
        return getattr(instance, attribute_name)

    def set_attribute(self, instance_id, attribute_name, new_value):
        """Set an attribute of an instance"""
        return self._dispatch_request(__E_SET_ATTRIBUTE__, instance_id, attribute_name, new_value)

    def _directive_set_attribute(self, directive_body):
        """Directive for :py:meth:`set_attribute`"""
        inst_id, attribute_name, new_value = directive_body
        try:
            instance = self._instances_alive_ref[inst_id]
        except KeyError:
            raise InstanceLookupError(instance_id=inst_id)
        return setattr(instance, attribute_name, new_value)

    def del_attribute(self, instance_id, attribute_name):
        """Delete an attribute of an instance"""
        return self._dispatch_request(__E_DEL_ATTRIBUTE__, instance_id, attribute_name)

    def _directive_del_attribute(self, directive_body):
        """Directive for :py:meth:`del_attribute`"""
        inst_id, attribute_name = directive_body
        try:
            instance = self._instances_alive_ref[inst_id]
        except KeyError:
            raise InstanceLookupError(instance_id=inst_id)
        return delattr(instance, attribute_name)

    def instantiate_class(self, cls, *cls_args, **cls_kwargs):
        """Instantiate a class, increment its reference count, and return its id"""
        return self._dispatch_request(__E_INSTANTIATE__, cls, cls_args, cls_kwargs)

    def _directive_instantiate(self, directive_body):
        """Directive for :py:meth:`instantiate_class`"""
        cls, cls_args, cls_kwargs = directive_body
        instance = cls(*cls_args, **cls_kwargs)
        if instance.__instance_id__ in self._instances_alive_ref:
            raise InstanceLookupError(instance_id=instance.__instance_id__)
        self._instances_keepalive[instance.__instance_id__] = [1, instance]
        self._instances_alive_ref[instance.__instance_id__] = instance
        return instance.__instance_id__

    def increment_instance_ref(self, instance_id):
        """Increment the reference count to an instance by one"""
        return self._dispatch_request(__E_REF_INCR__, instance_id)

    def _directive_ref_incr(self, directive_body):
        """Directive for :py:meth:`increment_instance_ref`"""
        inst_id = directive_body[0]
        try:
            self._instances_keepalive[inst_id][0] += 1
        except KeyError:
            try:
                instance = self._instances_alive_ref[inst_id]
            except KeyError:
                # fetch objects not created by kernel, but directly
                try:
                    instance = proxy_tracker.__active_instances__[kernel_state.TWIN_ID, inst_id]
                except KeyError:
                    raise InstanceLookupError(instance_id=inst_id)
                else:
                    self._instances_alive_ref[inst_id] = instance
            self._instances_keepalive[inst_id] = [1, instance]
        return self._instances_keepalive[inst_id][0]

    def decrement_instance_ref(self, instance_id):
        """Decrement the reference count to an instance by one"""
        return self._dispatch_request(__E_REF_DECR__, instance_id)

    def _directive_ref_decr(self, directive_body):
        """Directive for :py:meth:`decrement_instance_ref`"""
        inst_id = directive_body[0]
        try:
            self._instances_keepalive[inst_id][0] -= 1
            response = self._instances_keepalive[inst_id][0]
            if self._instances_keepalive[inst_id][0] <= 0:
                del self._instances_keepalive[inst_id]
        except KeyError:
            raise InstanceLookupError(instance_id=inst_id)
        return response

    def stop(self):
        """Shutdown the peer's server"""
        if self._dispatch_request(__E_SHUTDOWN__, 'stop'):
            return True
        return False

    @staticmethod
    def _directive_shutdown(directive_body):
        """Directive for :py:meth:`stop`"""
        message = directive_body[0]
        raise StopTwinterpreter(message=message, exit_code=0)

    def __repr__(self):
        return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())
