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
from __future__ import print_function

import sys
import os
import time
import logging
import weakref

from cpy2py.twinterpreter.kernel_state import __kernels__

from cpy2py.utility.exceptions import format_exception, CPy2PyException
from cpy2py.ipyc import stdstream, ipyc_exceptions
from cpy2py.twinterpreter.kernel_exceptions import TwinterpeterTerminated

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


class SingleThreadKernel(object):
    """
    Default kernel for handling requests between interpeters

    Any connection between twinterpreters is handled by two kernels, one in each
    twinterpreter. In each twinterpreter, the local kernel provides as a client
    interface for dispatching calls. At the same time, it acts as a server that
    handles requests from its peer.

    The kernels assume that they have been setup properly. Use
    :py:class:`~TwinMaster` start kernel peers.

    :param peer_id: id of the kernel/twinterpreter this kernel is peered with
    :type peer_id: str
    :param ipc: :py:mod:`~IPyC` connecting to other kernel
    :type ipc: :py:class:`~StdIPC`
    """

    def __new__(cls, peer_id, *args, **kwargs):  # pylint: disable=unused-argument
        assert peer_id not in __kernels__, 'Twinterpreters must have unique IDs'
        __kernels__[peer_id] = object.__new__(cls)
        return __kernels__[peer_id]

    def __init__(self, peer_id, ipc=stdstream.StdIPC()):
        self._logger = logging.getLogger('__cpy2py__.%s.%s' % (os.path.basename(sys.executable), peer_id))
        self.peer_id = peer_id
        self.ipc = ipc
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

    def run(self):
        """
        Run the kernel request server

        :returns: exit code indicating potential failure
        """
        exit_code, request_id = 1, None
        self._logger.warning('Starting @ %s', time.asctime())
        try:
            while True:
                self._logger.warning('Listening')
                request_id, directive = self.ipc.receive()
                self._serve_request(request_id, directive)
        except StopTwinterpreter as err:
            self.ipc.send((request_id, __E_SHUTDOWN__, err.exit_code))
        except ipyc_exceptions.IPyCTerminated:
            exit_code = 0
        except Exception:  # pylint: disable=broad-except
            self._logger.critical('TWIN KERNEL INTERNAL EXCEPTION')
            format_exception(self._logger, 3)
        finally:
            self._logger.critical('TWIN KERNEL SHUTDOWN: %d', exit_code)
            del __kernels__[self.peer_id]
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
            self.ipc.send((request_id, __E_EXCEPTION__, err))
            self._logger.critical('TWIN KERNEL PAYLOAD EXCEPTION')
            format_exception(self._logger, 3)
            if isinstance(err, (KeyboardInterrupt, SystemExit)):
                raise StopTwinterpreter(message=err.__class__.__name__, exit_code=1)
        else:
            self.ipc.send((request_id, __E_SUCCESS__, response))

    # dispatching: execute actions in other interpeter
    def _dispatch_request(self, request_type, *args):
        """Forward a request to peer and return result"""
        self._request_id += 1
        my_id = self._request_id
        try:
            self.ipc.send((my_id, (request_type, args)))
            request_id, result_type, result_body = self.ipc.receive()
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
        return getattr(self._instances_alive_ref[inst_id], method_name)(*method_args, **method_kwargs)

    def get_attribute(self, instance_id, attribute_name):
        """Get an attribute of an instance"""
        return self._dispatch_request(__E_GET_ATTRIBUTE__, instance_id, attribute_name)

    def _directive_get_attribute(self, directive_body):
        """Directive for :py:meth:`get_attribute`"""
        inst_id, attribute_name = directive_body
        return getattr(self._instances_alive_ref[inst_id], attribute_name)

    def set_attribute(self, instance_id, attribute_name, new_value):
        """Set an attribute of an instance"""
        return self._dispatch_request(__E_SET_ATTRIBUTE__, instance_id, attribute_name, new_value)

    def _directive_set_attribute(self, directive_body):
        """Directive for :py:meth:`set_attribute`"""
        inst_id, attribute_name, new_value = directive_body
        return setattr(self._instances_alive_ref[inst_id], attribute_name, new_value)

    def del_attribute(self, instance_id, attribute_name):
        """Delete an attribute of an instance"""
        return self._dispatch_request(__E_DEL_ATTRIBUTE__, instance_id, attribute_name)

    def _directive_del_attribute(self, directive_body):
        """Directive for :py:meth:`del_attribute`"""
        inst_id, attribute_name = directive_body
        return delattr(self._instances_alive_ref[inst_id], attribute_name)

    def instantiate_class(self, cls, *cls_args, **cls_kwargs):
        """Instantiate a class, increment its reference count, and return its id"""
        return self._dispatch_request(__E_INSTANTIATE__, cls, cls_args, cls_kwargs)

    def _directive_instantiate(self, directive_body):
        """Directive for :py:meth:`instantiate_class`"""
        cls, cls_args, cls_kwargs = directive_body
        instance = cls(*cls_args, **cls_kwargs)
        self._instances_keepalive[id(instance)] = [1, instance]
        self._instances_alive_ref[id(instance)] = instance
        return id(instance)

    def decrement_instance_ref(self, instance_id):
        """Decrement the reference count to an instance by one"""
        return self._dispatch_request(__E_REF_DECR__, instance_id)

    def _directive_ref_decr(self, directive_body):
        """Directive for :py:meth:`decrement_instance_ref`"""
        inst_id = directive_body[0]
        self._instances_keepalive[inst_id][0] -= 1
        response = self._instances_keepalive[inst_id][0]
        if self._instances_keepalive[inst_id][0] <= 0:
            del self._instances_keepalive[inst_id]
        return response

    def increment_instance_ref(self, instance_id):
        """Increment the reference count to an instance by one"""
        return self._dispatch_request(__E_REF_INCR__, instance_id)

    def _directive_ref_incr(self, directive_body):
        """Directive for :py:meth:`increment_instance_ref`"""
        inst_id = directive_body[0]
        try:
            self._instances_keepalive[inst_id][0] += 1
        except KeyError:
            self._instances_keepalive[inst_id] = [1, self._instances_alive_ref[inst_id]]
        return self._instances_keepalive[inst_id][0]

    def stop(self):
        """Shutdown the peer's server"""
        if self._dispatch_request(__E_SHUTDOWN__, 'stop'):
            del __kernels__[self.peer_id]
            return True
        return False

    @staticmethod
    def _directive_shutdown(directive_body):
        """Directive for :py:meth:`stop`"""
        message = directive_body[0]
        raise StopTwinterpreter(message=message, exit_code=0)

    def __repr__(self):
        return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())
