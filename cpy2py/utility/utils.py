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
import random

from .compat import rangex


_UPPERCASE_ORD = (ord('A'), ord('Z'))
_LOWERCASE_ORD = (ord('a'), ord('z'))


def random_str(length=16, upper_chars=0.5):
    return ''.join(
        chr(random.randint(*_UPPERCASE_ORD) if random.random() < upper_chars else random.randint(*_LOWERCASE_ORD))
        for _ in
        rangex(length)
    )
