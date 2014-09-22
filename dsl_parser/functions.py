########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

import abc

from dsl_parser import exceptions
from dsl_parser import scan

GET_INPUT_FUNCTION = 'get_input'
GET_PROPERTY_FUNCTION = 'get_property'
GET_ATTRIBUTE_FUNCTION = 'get_attribute'

SELF = 'SELF'
SOURCE = 'SOURCE'
TARGET = 'TARGET'


class Function(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, args, scope=None, context=None, path=None, raw=None):
        self.scope = scope
        self.context = context
        self.path = path
        self.raw = raw
        self._parse_args(args)

    @abc.abstractmethod
    def _parse_args(self, args):
        pass

    @abc.abstractmethod
    def validate(self, plan):
        pass

    @abc.abstractmethod
    def evaluate(self, plan):
        pass


class GetInput(Function):

    def __init__(self, args, **kwargs):
        self.input_name = None
        super(GetInput, self).__init__(args, **kwargs)

    def _parse_args(self, args):
        valid_args_type = isinstance(args, basestring)
        if not valid_args_type:
            raise ValueError(
                "get_input function argument should be a string in "
                "{} but is '{}'.".format(self.context, args))
        self.input_name = args

    def validate(self, plan):
        if self.input_name not in plan.inputs:
            raise exceptions.UnknownInputError(
                "{} get_input function references an "
                "unknown input '{}'.".format(self.context, self.input_name))

    def evaluate(self, plan):
        return plan.inputs[self.input_name]


class GetProperty(Function):

    def __init__(self, args, **kwargs):
        self.node_name = None
        self.property_name = None
        super(GetProperty, self).__init__(args, **kwargs)

    def _parse_args(self, args):
        if not isinstance(args, list) or len(args) < 2:
            raise ValueError(
                'Illegal arguments passed to {0} function. '
                'Expected: [ node_name, property_name ] but got: {1}.'.format(
                    GET_PROPERTY_FUNCTION, args))
        self.node_name = args[0]
        self.property_name = args[1]

    def validate(self, plan):
        self.evaluate(plan)

    def get_node_template(self, plan):
        if self.node_name == SELF:
            if self.scope != scan.NODE_TEMPLATE_SCOPE:
                raise ValueError(
                    '{0} can only be used in a context of node template but '
                    'appears in {1}.'.format(SELF, self.scope))
            node = self.context
        elif self.node_name in [SOURCE, TARGET]:
            if self.scope != scan.NODE_TEMPLATE_RELATIONSHIP_SCOPE:
                raise ValueError(
                    '{0} can only be used within a relationship but is used '
                    'in {1}'.format(self.node_name, self.path))
            if self.node_name == SOURCE:
                node = self.context['node_template']
            else:
                target_node = self.context['relationship']['target_id']
                node = [
                    x for x in plan.node_templates
                    if x['name'] == target_node][0]
        else:
            found = [
                x for x in plan.node_templates if self.node_name in x['id']]
            if len(found) == 0:
                raise KeyError(
                    "{0} function node reference '{1}' does not exist.".format(
                        GET_PROPERTY_FUNCTION, self.node_name))
            node = found[0]
        if self.property_name not in node['properties']:
            raise KeyError(
                "Node template property '{0}.properties.{1}' referenced "
                "from '{2}' doesn't exist.".format(node['name'],
                                                   self.property_name,
                                                   self.path))
        return node

    def evaluate(self, plan):
        return self.get_node_template(plan)['properties'][self.property_name]


class GetAttribute(Function):

    def __init__(self, args, **kwargs):
        self.node_name = None
        self.attribute_name = None
        super(GetAttribute, self).__init__(args, **kwargs)

    def _parse_args(self, args):
        if not isinstance(args, list) or len(args) < 2:
            raise ValueError(
                'Illegal arguments passed to {0} function. '
                'Expected: [ node_name, property_name ] but got: {1}.'.format(
                    GET_ATTRIBUTE_FUNCTION, args))
        self.node_name = args[0]
        self.attribute_name = args[1]

    def validate(self, plan):
        if self.scope != scan.OUTPUTS_SCOPE:
            raise ValueError('{0} function can only be used in outputs but is '
                             'used in {1}.'.format(GET_ATTRIBUTE_FUNCTION,
                                                   self.path))
        if self.node_name == SELF:
            raise ValueError('{0} cannot be used with {1} function in '
                             '{2}.'.format(SELF,
                                           GET_ATTRIBUTE_FUNCTION,
                                           self.path))
        found = [
            x for x in plan.node_templates if self.node_name in x['id']]
        if len(found) == 0:
            raise KeyError(
                "{0} function node reference '{1}' does not exist.".format(
                    GET_ATTRIBUTE_FUNCTION, self.node_name))

    def evaluate(self, plan):
        raise RuntimeError(
            '{0} function does not support evaluation.'.format(
                GET_ATTRIBUTE_FUNCTION))


TEMPLATE_FUNCTIONS = {
    GET_PROPERTY_FUNCTION: GetProperty,
    GET_ATTRIBUTE_FUNCTION: GetAttribute,
    GET_INPUT_FUNCTION: GetInput
}


def parse(raw_function, scope=None, context=None, path=None):
    if isinstance(raw_function, dict) and len(raw_function) == 1:
        func_name = raw_function.keys()[0]
        if func_name in TEMPLATE_FUNCTIONS:
            func_args = raw_function.values()[0]
            return TEMPLATE_FUNCTIONS[func_name](func_args,
                                                 scope=scope,
                                                 context=context,
                                                 path=path,
                                                 raw=raw_function)
    return raw_function


def evaluate_outputs(outputs_def, get_node_instances_method):
    """Evaluates an outputs definition containing intrinsic functions.

    :param outputs_def: Outputs definition.
    :param get_node_instances_method: A method for getting node instances.
    :return: Outputs dict.
    """
    ctx = {}
    outputs = {k: v['value'] for k, v in outputs_def.iteritems()}

    def handler(v, scope, context, path):
        func = parse(v, scope=scope, context=context, path=path)
        if isinstance(func, GetAttribute):
            attributes = []
            if 'node_instances' not in ctx:
                ctx['node_instances'] = get_node_instances_method()
            for instance in ctx['node_instances']:
                if instance.node_id == func.node_name:
                    attributes.append(
                        instance.runtime_properties.get(
                            func.attribute_name) if
                        instance.runtime_properties else None)
            if len(attributes) == 1:
                return attributes[0]
            elif len(attributes) == 0:
                raise exceptions.FunctionEvaluationError(
                    GET_ATTRIBUTE_FUNCTION,
                    'Node specified in function does not exist: {0}.'.format(
                        func.node_name)
                )
            else:
                raise exceptions.FunctionEvaluationError(
                    GET_ATTRIBUTE_FUNCTION,
                    'Multi instances of node "{0}" are not supported by '
                    'function.'.format(func.node_name))

    scan.scan_properties(outputs,
                         handler,
                         scope=scan.OUTPUTS_SCOPE,
                         context=outputs,
                         path='outputs',
                         replace=True)
    return outputs
