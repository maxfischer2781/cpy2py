# - # Copyright 2016 Max Fischer
# - #
# - # Licensed under the Apache License, Version 2.0 (the "License");
# - # you may not use this file except in compliance with the License.
# - # You may obtain a copy of the License at
# - #
# - # 	http://www.apache.org/licenses/LICENSE-2.0
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
import cpy2py.ipyc
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
__E_SUCCESS__ = 0
__E_EXCEPTION__ = 1


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

    def __init__(self, peer_id, ipc=cpy2py.ipyc.StdIPC()):
        self._logger = logging.getLogger('__cpy2py__.%s.%s' % (os.path.basename(sys.executable), peer_id))
        self.peer_id = peer_id
        self.ipc = ipc
        self._request_id = 0
        # instance_id => [ref_count, instance]
        self._instances_keepalive = {}
        # instance_id => instance
        self._instances_alive_ref = weakref.WeakValueDictionary()

    def run(self):
        """
        Run the kernel request server

        :returns: exit code indicating potential failure
        """
        exit_code = 1
        self._logger.warning('run @ %s', time.asctime())
        self._logger.warning('Starting')
        try:
            while True:
                self._logger.warning('Listening')
                request_id, directive = self.ipc.receive()
                self._logger.warning('Received: %d', request_id)
                self._logger.warning(repr(directive))
                try:
                    if directive[0] == __E_CALL_FUNC__:
                        self._logger.warning('Directive __E_CALL_FUNC__')
                        func_obj, func_args, func_kwargs = directive[1]
                        response = func_obj(*func_args, **func_kwargs)
                    elif directive[0] == __E_CALL_METHOD__:
                        self._logger.warning('Directive __E_CALL_METHOD__')
                        inst_id, method_name, method_args, method_kwargs = directive[1]
                        response = getattr(self._instances_alive_ref[inst_id], method_name)(*method_args,
                                                                                            **method_kwargs)
                    elif directive[0] == __E_GET_ATTRIBUTE__:
                        self._logger.warning('Directive __E_GET_MEMBER__')
                        inst_id, attribute_name = directive[1]
                        response = getattr(self._instances_alive_ref[inst_id], attribute_name)
                    elif directive[0] == __E_SET_ATTRIBUTE__:
                        self._logger.warning('Directive __E_SET_ATTRIBUTE__')
                        inst_id, attribute_name, new_value = directive[1]
                        response = setattr(self._instances_alive_ref[inst_id], attribute_name, new_value)
                    elif directive[0] == __E_DEL_ATTRIBUTE__:
                        self._logger.warning('Directive __E_DEL_ATTRIBUTE__')
                        inst_id, attribute_name = directive[1]
                        response = delattr(self._instances_alive_ref[inst_id], attribute_name)
                    elif directive[0] == __E_INSTANTIATE__:
                        self._logger.warning('Directive __E_INSTANTIATE__')
                        cls, cls_args, cls_kwargs = directive[1]
                        instance = cls(*cls_args, **cls_kwargs)
                        self._instances_keepalive[id(instance)] = [1, instance]
                        self._instances_alive_ref[id(instance)] = instance
                        response = id(instance)
                    elif directive[0] == __E_REF_DECR__:
                        self._logger.warning('Directive __E_REF_DECR__')
                        inst_id = directive[1][0]
                        self._instances_keepalive[inst_id][0] -= 1
                        response = self._instances_keepalive[inst_id][0]
                        if self._instances_keepalive[inst_id][0] <= 0:
                            del self._instances_keepalive[inst_id]
                    elif directive[0] == __E_REF_INCR__:
                        self._logger.warning('Directive __E_REF_INCR__')
                        inst_id = directive[1][0]
                        try:
                            self._instances_keepalive[inst_id][0] += 1
                        except KeyError:
                            self._instances_keepalive[inst_id] = [1, self._instances_alive_ref[inst_id]]
                        response = self._instances_keepalive[inst_id][0]
                    elif directive[0] == __E_SHUTDOWN__:
                        self._logger.warning('Directive __E_SHUTDOWN__')
                        del __kernels__[self.peer_id]
                        self.ipc.send((request_id, __E_SHUTDOWN__, True))
                        break
                    else:
                        raise RuntimeError
                # catch internal errors to reraise them
                except CPy2PyException:
                    raise
                # send everything else back to calling scope
                except Exception as err:  # pylint: disable=broad-except
                    self.ipc.send((request_id, __E_EXCEPTION__, err))
                    self._logger.critical('TWIN KERNEL PAYLOAD EXCEPTION')
                    format_exception(self._logger, 3)
                    if isinstance(err, KeyboardInterrupt):
                        break
                else:
                    self.ipc.send((request_id, __E_SUCCESS__, response))
        except cpy2py.ipyc.IPyCTerminated:
            exit_code = 0
        except Exception:  # pylint: disable=broad-except
            self._logger.critical('TWIN KERNEL EXCEPTION')
            format_exception(self._logger, 3)
        finally:
            # always free resources and exit when the kernel stops
            del self._instances_keepalive
            del self.ipc
        self._logger.critical('TWIN KERNEL SHUTDOWN: %d', exit_code)
        return exit_code

    # dispatching: execute actions in other interpeter
    def _dispatch_request(self, request_type, *args):
        """Forward a request to peer and return result"""
        self._request_id += 1
        my_id = self._request_id
        try:
            self.ipc.send((my_id, (request_type, args)))
            request_id, result_type, result_body = self.ipc.receive()
        except cpy2py.ipyc.IPyCTerminated:
            raise TwinterpeterTerminated(twin_id=self.peer_id)
        assert request_id == my_id, 'kernel messages out of order'
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

    def dispatch_method_call(self, instance_id, method_name, *method_args, **methods_kwargs):
        """Execute a method call and return the result"""
        return self._dispatch_request(__E_CALL_METHOD__, instance_id, method_name, method_args, methods_kwargs)

    def get_attribute(self, instance_id, attribute_name):
        """Get an attribute of an instance"""
        return self._dispatch_request(__E_GET_ATTRIBUTE__, instance_id, attribute_name)

    def set_attribute(self, instance_id, attribute_name, new_value):
        """Set an attribute of an instance"""
        return self._dispatch_request(__E_SET_ATTRIBUTE__, instance_id, attribute_name, new_value)

    def del_attribute(self, instance_id, attribute_name):
        """Delete an attribute of an instance"""
        return self._dispatch_request(__E_DEL_ATTRIBUTE__, instance_id, attribute_name)

    def instantiate_class(self, cls, *cls_args, **cls_kwargs):
        """Instantiate a class, increments its reference count, and return its id"""
        return self._dispatch_request(__E_INSTANTIATE__, cls, cls_args, cls_kwargs)

    def decrement_instance_ref(self, instance_id):
        """Decrement the reference count to an instance by one"""
        return self._dispatch_request(__E_REF_DECR__, instance_id)

    def increment_instance_ref(self, instance_id):
        """Increment the reference count to an instance by one"""
        return self._dispatch_request(__E_REF_INCR__, instance_id)

    def stop(self):
        """Shutdown the peer's server"""
        if self._dispatch_request(__E_SHUTDOWN__):
            del __kernels__[self.peer_id]
            return True
        return False

    def __repr__(self):
        return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())
