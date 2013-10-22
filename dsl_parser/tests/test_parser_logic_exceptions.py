########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

__author__ = 'ran'

import os
from dsl_parser.parser import DSLParsingLogicException, parse_from_file
from dsl_parser.tests.abstract_test_parser import AbstractTestParser


class TestParserLogicExceptions(AbstractTestParser):

    def test_no_type_definition(self):
        self._assert_dsl_parsing_exception_error_code(self.BASIC_APPLICATION_TEMPLATE_SECTION, 7, DSLParsingLogicException)

    def test_explicit_interface_with_missing_plugin(self):
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + self.BASIC_INTERFACE_AND_PLUGIN + """
types:
    test_type:
        interfaces:
            -   test_interface1: "missing_plugin"
        properties:
            install_agent: 'false'
"""
        self._assert_dsl_parsing_exception_error_code(yaml, 10, DSLParsingLogicException)

    def test_missing_interface_definition(self):
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + self.BASIC_INTERFACE_AND_PLUGIN + """
types:
    test_type:
        interfaces:
            -   missing_interface: "test_plugin2"
        properties:
            install_agent: 'false'

plugins:
    test_plugin2:
        derived_from: "cloudify.tosca.artifacts.agent_plugin"
        properties:
            interface: "missing_interface"
            url: "http://test_url2.zip"
"""
        self._assert_dsl_parsing_exception_error_code(yaml, 9, DSLParsingLogicException)

    def test_type_with_interface_with_explicit_illegal_plugin(self):
        #testing to see what happens when the plugin which is explicitly declared for an interface is in fact
        #a plugin which doesn't implement the said interface (even if it supports another interface with same
        # name operations)
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + """
interfaces:
    test_interface1:
        operations:
            -   "install"
            -   "terminate"
    test_interface2:
        operations:
            -   "install"
            -   "terminate"

plugins:
    test_plugin:
        derived_from: "cloudify.tosca.artifacts.agent_plugin"
        properties:
            interface: "test_interface1"
            url: "http://test_url.zip"

types:
    test_type:
        interfaces:
            -   test_interface2: "test_plugin"
        """
        self._assert_dsl_parsing_exception_error_code(yaml, 6, DSLParsingLogicException)

    def test_implicit_interface_with_no_matching_plugins(self):
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + self.BASIC_INTERFACE_AND_PLUGIN + """
types:
    test_type:
        interfaces:
            -   test_interface2
        properties:
            install_agent: 'false'

interfaces:
    test_interface2:
        operations:
            -   "install"
            -   "terminate"
"""
        self._assert_dsl_parsing_exception_error_code(yaml, 11, DSLParsingLogicException)

    def test_implicit_interface_with_ambiguous_matches(self):
        yaml = self.create_yaml_with_imports([self.APPLICATION_TEMPLATE_WITH_INTERFACES_AND_PLUGINS]) + """
plugins:
    other_test_plugin:
        derived_from: "cloudify.tosca.artifacts.agent_plugin"
        properties:
            interface: "test_interface1"
            url: "http://other_test_url.zip"
"""
        self._assert_dsl_parsing_exception_error_code(yaml, 12, DSLParsingLogicException)

    def test_dsl_with_interface_without_plugin(self):
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + self.BASIC_TYPE + """
interfaces:
    test_interface1:
        operations:
            -   "install"
            -   "terminate"
        """
        self._assert_dsl_parsing_exception_error_code(yaml, 5, DSLParsingLogicException)

    def test_merge_non_mergeable_properties_on_import(self):
        yaml = self.create_yaml_with_imports([self.BASIC_APPLICATION_TEMPLATE_SECTION, self.BASIC_INTERFACE_AND_PLUGIN]) + """
application_template:
    name: test_app2
    topology:
        -   name: test_node2
            type: test_type
            properties:
                key: "val"
        """
        self._assert_dsl_parsing_exception_error_code(yaml, 3, DSLParsingLogicException)

    def test_illegal_merge_on_nested_mergeable_rules_on_import(self):
        imported_yaml = self.MINIMAL_APPLICATION_TEMPLATE + """
policies:
    rules:
        rule1:
            message: "custom message"
            rule: "custom clojure code"
            """
        yaml = self.create_yaml_with_imports([imported_yaml]) + """
policies:
    rules:
        rule1:
            message: "some other message"
            rule: "some other code"
            """
        self._assert_dsl_parsing_exception_error_code(yaml, 4, DSLParsingLogicException)

    def test_recursive_imports_with_inner_circular(self):
        bottom_level_yaml = """
imports:
    -   {0}
        """.format(os.path.join(self._temp_dir, "mid_level.yaml")) + self.BASIC_TYPE
        bottom_file_name = self.make_yaml_file(bottom_level_yaml)

        mid_level_yaml = self.BASIC_INTERFACE_AND_PLUGIN + """
imports:
    -   {0}""".format(bottom_file_name)
        mid_file_name = self.make_file_with_name(mid_level_yaml, 'mid_level.yaml')

        top_level_yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + """
imports:
    -   {0}""".format(mid_file_name)

        ex = self._assert_dsl_parsing_exception_error_code(top_level_yaml, 8, DSLParsingLogicException)
        expected_circular_path = [mid_file_name, bottom_file_name, mid_file_name]
        self.assertEquals(expected_circular_path, ex.circular_path)

    def test_recursive_imports_with_complete_circle(self):
        bottom_level_yaml = """
imports:
    -   {0}
            """.format(os.path.join(self._temp_dir, "top_level.yaml")) + self.BASIC_TYPE
        bottom_file_name = self.make_yaml_file(bottom_level_yaml)

        mid_level_yaml = self.BASIC_INTERFACE_AND_PLUGIN + """
imports:
    -   {0}""".format(bottom_file_name)
        mid_file_name = self.make_yaml_file(mid_level_yaml)

        top_level_yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + """
imports:
    -   {0}""".format(mid_file_name)
        top_file_name = self.make_file_with_name(top_level_yaml, 'top_level.yaml')
        ex = self._assert_dsl_parsing_exception_error_code(top_file_name, 8, DSLParsingLogicException, parse_from_file)
        expected_circular_path = [top_file_name, mid_file_name, bottom_file_name, top_file_name]
        self.assertEquals(expected_circular_path, ex.circular_path)

    def test_type_derive_non_from_none_existing(self):
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + """
types:
    test_type:
        interfaces:
            -   test_interface1
        derived_from: "non_existing_type_parent"
        """
        self._assert_dsl_parsing_exception_error_code(yaml, 14, DSLParsingLogicException)

    def test_import_bad_path(self):
        yaml = """
imports:
    -   fake-file.yaml
        """
        self._assert_dsl_parsing_exception_error_code(yaml, 13, DSLParsingLogicException)

    def test_cyclic_dependency(self):
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + """
types:
    test_type:
        derived_from: "test_type_parent"

    test_type_parent:
        derived_from: "test_type_grandparent"

    test_type_grandparent:
        derived_from: "test_type"
    """
        ex = self._assert_dsl_parsing_exception_error_code(yaml, 100, DSLParsingLogicException)
        expected_circular_dependency = ['test_type', 'test_type_parent', 'test_type_grandparent', 'test_type']
        self.assertEquals(expected_circular_dependency, ex.circular_dependency)

    def test_node_duplicate_name(self):
        yaml = """
application_template:
    name: test_app
    topology:
    -   name: test_node
        type: test_type
        properties:
            key: "val"
    -   name: test_node
        type: test_type
        properties:
            key: "val"

types:
    test_type: {}
"""
        ex = self._assert_dsl_parsing_exception_error_code(yaml, 101, DSLParsingLogicException)
        self.assertEquals('test_node', ex.duplicate_node_name)

    def test_first_level_workflows_unavailable_ref(self):
        ref_alias = 'custom_ref_alias'
        yaml = self.MINIMAL_APPLICATION_TEMPLATE + """
workflows:
    install:
        ref: {0}
        """.format(ref_alias)
        self._assert_dsl_parsing_exception_error_code(yaml, 15)

    def test_type_duplicate_interface(self):
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + self.BASIC_INTERFACE_AND_PLUGIN + """
types:
    test_type:
        interfaces:
            -   test_interface1
            -   test_interface1: test_plugin
"""
        ex = self._assert_dsl_parsing_exception_error_code(yaml, 102, DSLParsingLogicException)
        self.assertEquals('test_node', ex.node_name)
        self.assertEquals('test_interface1', ex.duplicate_interface_name)

    def test_first_level_policy_unavailable_ref(self):
        ref_alias = 'custom_ref_alias'
        yaml = self.MINIMAL_APPLICATION_TEMPLATE + """
policies:
    types:
        custom_policy:
            message: "custom message"
            ref: {0}
        """.format(ref_alias)
        self._assert_dsl_parsing_exception_error_code(yaml, 15)

    def test_illegal_merge_on_mergeable_properties_on_import(self):
        yaml = self.create_yaml_with_imports([self.BASIC_APPLICATION_TEMPLATE_SECTION, self.BASIC_INTERFACE_AND_PLUGIN]) + """
plugins:
    test_plugin:
        properties:
            interface: "test_interface2"
            url: "http://test_url2.zip"
types:
    test_type:
        interfaces:
            -   test_interface1
            -   test_interface2

interfaces:
    test_interface2:
        operations:
            -   "start"
            -   "shutdown"
        """
        self._assert_dsl_parsing_exception_error_code(yaml, 4, DSLParsingLogicException)

    def test_illegal_merge_on_nested_mergeable_policies_events_on_import(self):
        imported_yaml = self.MINIMAL_APPLICATION_TEMPLATE + """
policies:
    types:
        policy1:
            message: "custom message"
            policy: "custom clojure code"
            """
        yaml = self.create_yaml_with_imports([imported_yaml]) + """
policies:
    types:
        policy1:
            message: "some other message"
            policy: "some other code"
            """
        self._assert_dsl_parsing_exception_error_code(yaml, 4, DSLParsingLogicException)

    def test_node_with_undefined_policy_event(self):
        yaml = self.POLICIES_SECTION + self.MINIMAL_APPLICATION_TEMPLATE + """
            policies:
                undefined_policy:
                    rules:
                        -   type: "test_rule"
                            properties:
                                state: "custom state"
                                value: "custom value"
                """
        self._assert_dsl_parsing_exception_error_code(yaml, 16, DSLParsingLogicException)

    def test_node_with_undefined_rule(self):
        yaml = self.POLICIES_SECTION + self.MINIMAL_APPLICATION_TEMPLATE + """
            policies:
                test_policy:
                    rules:
                        -   type: "undefined_rule"
                            properties:
                                state: "custom state"
                                value: "custom value"
                """
        self._assert_dsl_parsing_exception_error_code(yaml, 17, DSLParsingLogicException)

    def test_type_with_undefined_policy_event(self):
        yaml = self.POLICIES_SECTION + self.BASIC_APPLICATION_TEMPLATE_SECTION + """
types:
    test_type:
        policies:
            undefined_policy:
                rules:
                    -   type: "test_rule"
                        properties:
                            state: "custom state"
                            value: "custom value"
                """
        self._assert_dsl_parsing_exception_error_code(yaml, 16, DSLParsingLogicException)

    def test_type_with_undefined_rule(self):
        yaml = self.POLICIES_SECTION + self.BASIC_APPLICATION_TEMPLATE_SECTION + """
types:
    test_type:
        policies:
            test_policy:
                rules:
                    -   type: "undefined_rule"
                        properties:
                            state: "custom state"
                            value: "custom value"
                """
        self._assert_dsl_parsing_exception_error_code(yaml, 17, DSLParsingLogicException)

    def test_plugin_with_wrongful_derived_from_field(self):
        yaml = self.BASIC_APPLICATION_TEMPLATE_SECTION + """
interfaces:
    test_interface1:
        operations:
            -   "install"

plugins:
    test_plugin:
        derived_from: "bad value"
        properties:
            interface: "test_interface1"
            url: "http://test_url.zip"

types:
    test_type:
        interfaces:
            -   test_interface1: "test_plugin"
        """
        self._assert_dsl_parsing_exception_error_code(yaml, 18, DSLParsingLogicException)