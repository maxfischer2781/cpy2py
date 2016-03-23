#!/usr/bin/python
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
import cpy2py.twinterpreter.kernel
import cpy2py.twinterpreter.twin_pypy
import example_module
import time

if __name__ == "__main__":
	twinterpreter = cpy2py.twinterpreter.twin_pypy.TwinPyPy()
	twinterpreter.start()
	print cpy2py.twinterpreter.kernel.__kernels__
	print example_module.TwinTest()
	twinterpreter.stop()
time.sleep(0.1)
