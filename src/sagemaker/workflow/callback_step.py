# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""The step definitions for workflow."""
from __future__ import absolute_import

from typing import List, Dict
from enum import Enum

import attr

from sagemaker.workflow.entities import (
    RequestType,
)
from sagemaker.workflow.properties import (
    Properties,
)
from sagemaker.workflow.entities import (
    DefaultEnumMeta,
)
from sagemaker.workflow.steps import Step, StepTypeEnum, CacheConfig


class CallbackOutputTypeEnum(Enum, metaclass=DefaultEnumMeta):
    """CallbackOutput type enum."""

    String = "String"
    Integer = "Integer"
    Boolean = "Boolean"
    Float = "Float"


@attr.s
class CallbackOutput:
    """Output for a callback step.

    Attributes:
        output_name (str): The output name
        output_type (CallbackOutputTypeEnum): The output type
    """

    output_name: str = attr.ib(default=None)
    output_type: CallbackOutputTypeEnum = attr.ib(default=CallbackOutputTypeEnum.String.value)

    def to_request(self) -> RequestType:
        """Get the request structure for workflow service calls."""
        return {
            "OutputName": self.output_name,
            "OutputType": self.output_type.value,
        }

    @property
    def expr(self) -> Dict[str, str]:
        """The 'Get' expression dict for a `Parameter`."""
        return CallbackOutput._expr(self.output_name)

    @classmethod
    def _expr(cls, name):
        """An internal classmethod for the 'Get' expression dict for a `CallbackOutput`.

        Args:
            name (str): The name of the callback output.
        """
        return {"Get": f"Steps.{name}.OutputParameters['{name}']"}


class CallbackStep(Step):
    """Callback step for workflow."""

    def __init__(
        self,
        name: str,
        sqs_queue_url: str,
        inputs: dict,
        outputs: List[CallbackOutput],
        cache_config: CacheConfig = None,
        depends_on: List[str] = None,
    ):
        """Constructs a CallbackStep.

        Args:
            name (str): The name of the callback step.
            sqs_queue_url (str): An SQS queue URL for receiving callback messages.
            inputs (dict): Input arguments that will be provided
                in the SQS message body of callback messages.
            outputs (List[CallbackOutput]): Outputs that can be provided when completing a callback.
            cache_config (CacheConfig):  A `sagemaker.workflow.steps.CacheConfig` instance.
            depends_on (List[str]): A list of step names this `sagemaker.workflow.steps.TransformStep`
                depends on
        """
        super(CallbackStep, self).__init__(name, StepTypeEnum.CALLBACK, depends_on)
        self.sqs_queue_url = sqs_queue_url
        self.outputs = outputs
        self.cache_config = cache_config
        self.inputs = inputs

        root_path = f"Steps.{name}"
        root_prop = Properties(path=root_path)

        property_dict = {}
        for output in outputs:
            property_dict[output.output_name] = Properties(
                f"{root_path}.OutputParameters['{output.output_name}']"
            )

        root_prop.__dict__["Outputs"] = property_dict
        self._properties = root_prop

    @property
    def arguments(self) -> RequestType:
        """The arguments dict that is used to define the callback step."""
        return self.inputs

    @property
    def properties(self):
        """A Properties object representing the output parameters of the callback step."""
        return self._properties

    def to_request(self) -> RequestType:
        """Updates the dictionary with cache configuration."""
        request_dict = super().to_request()
        if self.cache_config:
            request_dict.update(self.cache_config.config)

        request_dict["SqsQueueUrl"] = self.sqs_queue_url
        request_dict["OutputParameters"] = list(map(lambda op: op.to_request(), self.outputs))

        return request_dict
