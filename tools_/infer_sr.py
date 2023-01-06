# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

import os
import sys
import json
from PIL import Image
import cv2

__dir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, __dir__)
sys.path.insert(0, os.path.abspath(os.path.join(__dir__, '..')))

os.environ["FLAGS_allocator_strategy"] = 'auto_growth'

import paddle

from ppocr.data import create_operators, transform
from ppocr.modeling.architectures import build_model
from ppocr.postprocess import build_post_process
from ppocr.utils.save_load import load_model
from ppocr.utils.utility import get_image_file_list
import tools_.program as program


def main():
    global_config = config['Global']

    # build post process
    post_process_class = build_post_process(config['PostProcess'],
                                            global_config)

    # sr transform
    config['Architecture']["Transform"]['infer_mode'] = True

    model = build_model(config['Architecture'])

    load_model(config, model)

    # create data ops
    transforms = []
    for op in config['Eval']['dataset']['transforms']:
        op_name = list(op)[0]
        if 'Label' in op_name:
            continue
        elif op_name in ['SRResize']:
            op[op_name]['infer_mode'] = True
        elif op_name == 'KeepKeys':
            op[op_name]['keep_keys'] = ['img_lr']
        transforms.append(op)
    global_config['infer_mode'] = True
    ops = create_operators(transforms, global_config)

    save_visual_path = config['Global'].get('save_visual', "infer_result/")
    if not os.path.exists(os.path.dirname(save_visual_path)):
        os.makedirs(os.path.dirname(save_visual_path))

    model.eval()
    for file in get_image_file_list(config['Global']['infer_img']):
        logger.info("infer_img: {}".format(file))
        img = Image.open(file).convert("RGB")
        data = {'image_lr': img}
        batch = transform(data, ops)
        images = np.expand_dims(batch[0], axis=0)
        images = paddle.to_tensor(images)

        preds = model(images)
        sr_img = preds["sr_img"][0]
        lr_img = preds["lr_img"][0]
        fm_sr = (sr_img.numpy() * 255).transpose(1, 2, 0).astype(np.uint8)
        fm_lr = (lr_img.numpy() * 255).transpose(1, 2, 0).astype(np.uint8)
        img_name_pure = os.path.split(file)[-1]
        cv2.imwrite("{}/sr_{}".format(save_visual_path, img_name_pure),
                    fm_sr[:, :, ::-1])
        logger.info("The visualized image saved in infer_result/sr_{}".format(
            img_name_pure))

    logger.info("success!")


if __name__ == '__main__':
    config, device, logger, vdl_writer = program.preprocess()
    main()
