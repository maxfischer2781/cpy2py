notice_template = """
%(package_name)s (%(repo_url)s)

Copyright (C) %(dev_years)s %(primary_authors)s

--------------------------------------------------------------------------------

This product includes backported python library code (http://www.python.org)
Copyright (C) 2001-2016 Python Software Foundation.
Licensed under the Python Software Foundation License.
""".strip()

license_header_template = """
Copyright %(dev_years)s %(primary_authors)s

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
""".strip()

primary_author_list = [
	"Max Fischer"
]

contributor_aliases = {  # map git-name => real-name

}
