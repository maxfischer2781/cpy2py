import threading

from ..kernel.flavours import async, threaded, single

from . import bootstrap


class TwinKernelMaster(object):
    default_kernels = {
        'single': single,
        'async': async,
        'multi': threaded,
    }

    @property
    def alive(self):
        return self.client is not None and self.server is not None

    @property
    def cli_args(self):
        return (
            '--server-ipyc', bootstrap.dump_connector(connector=self._client_ipyc.connector),
            '--client-ipyc', bootstrap.dump_connector(connector=self._server_ipyc.connector),
            '--ipyc-pkl-protocol', str(self._protocol),
            '--kernel', bootstrap.dump_kernel(kernel_client=self._kernel_client, kernel_server=self._kernel_server),
        )

    def __init__(self, twin_id, kernel, ipyc, protocol):
        self.twin_id = twin_id
        self._client_ipyc = ipyc()
        self._server_ipyc = ipyc()
        self._kernel_client, self._kernel_server = self._resolve_kernel_spec(kernel)
        self._protocol = protocol
        self._server_thread = None
        self.client, self.server = None, None

    def accept(self):
        if self.client is not None or self.server is not None:
            raise RuntimeError('%s cannot accept multiple peers' % self.__class__.__name__)
        self.client = self._kernel_client(
            self.twin_id,
            ipyc=self._client_ipyc,
            pickle_protocol=self._protocol,
        )
        self.server = self._kernel_server(
            self.twin_id,
            ipyc=self._server_ipyc,
            pickle_protocol=self._protocol,
        )
        self._server_thread = threading.Thread(target=self.server.run)
        self._server_thread.daemon = True
        self._server_thread.start()

    def shutdown(self):
        if self.client is None and self.server is None:
            return
        # stop the client first - the remote server will go down as a result
        self.client.stop()
        self.server.stop()
        self.client, self.server = None, None

    def _resolve_kernel_spec(self, kernel_spec):
        kernel_spec = kernel_spec or 'single'
        kernel_arg = self.default_kernels.get(kernel_spec, kernel_spec)
        try:
            client, server = kernel_arg.CLIENT, kernel_arg.SERVER
        except AttributeError:
            try:
                client, server = kernel_arg
            except (TypeError, ValueError):
                raise ValueError("Expected 'kernel' to reference client and server")
        return client, server
