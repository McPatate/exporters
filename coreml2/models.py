# Copyright 2022 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import OrderedDict
from typing import Any, Mapping

from coremltools.converters.mil import Builder as mb

from .config import CoreMLConfig


class BeitCoreMLConfig(CoreMLConfig):
    pass


class ConvNextCoreMLConfig(CoreMLConfig):
    pass


class CvTCoreMLConfig(CoreMLConfig):
    @property
    def outputs(self) -> OrderedDict[str, Mapping[int, str]]:
        if self.task == "default":
            return OrderedDict(
                [
                    (
                        "last_hidden_state",
                        {
                            "description": "Sequence of hidden-states at the output of the last layer of the model",
                        }
                    ),
                    (
                        "cls_token_value",
                        {
                            "description": "Classification token at the output of the last layer of the model",
                        }
                    ),
                ]
            )
        else:
            return super().outputs

    def patch_pytorch_ops(self):
        # coremltools does support einsum but not the equation "bhlt,bhtv->bhlv"
        # so override the implementation of this operation
        def einsum(context, node):
            from coremltools.converters.mil.frontend._utils import build_einsum_mil

            a = context[node.inputs[1]][0]
            b = context[node.inputs[1]][1]
            equation = context[node.inputs[0]].val

            if equation == "bhlt,bhtv->bhlv":
                x = mb.matmul(x=a, y=b, transpose_x=False, transpose_y=False, name=node.name)
            else:
                x = build_einsum_mil(a, b, equation, node.name)

            context.add(x)

        return { "einsum": einsum }


class LeViTCoreMLConfig(CoreMLConfig):
    def patch_pytorch_ops(self):
        def reshape_as(context, node):
            a = context[node.inputs[0]]
            b = context[node.inputs[1]]
            y = mb.shape(x=b)
            x = mb.reshape(x=a, shape=y, name=node.name)
            context.add(x)

        return { "reshape_as": reshape_as }


class MobileViTCoreMLConfig(CoreMLConfig):
    @property
    def inputs(self) -> OrderedDict[str, Mapping[str, Any]]:
        input_defs = super().inputs
        input_defs["image"]["color_layout"] = "BGR"
        return input_defs


class SegformerCoreMLConfig(CoreMLConfig):
    pass


class ViTCoreMLConfig(CoreMLConfig):
    pass


class YolosCoreMLConfig(CoreMLConfig):
    def patch_pytorch_ops(self):
        # There is no bicubic upsampling in Core ML, so we'll have to use bilinear.
        # Still seems to work well enough. Note: the bilinear resize is applied to
        # constant tensors, so we could actually remove this op completely!
        def upsample_bicubic2d(context, node):
            a = context[node.inputs[0]]
            b = context[node.inputs[1]]
            x = mb.resize_bilinear(x=a, target_size_height=b.val[0], target_size_width=b.val[1], name=node.name)
            context.add(x)

        return { "upsample_bicubic2d": upsample_bicubic2d }