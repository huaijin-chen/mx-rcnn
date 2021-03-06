import argparse
import pprint
import mxnet as mx

from ..config import config, default, generate_config
from ..symbol import *
from ..dataset import *
from ..core.loader import TestLoader
from ..core.tester import Predictor, pred_eval
from ..utils.load_model import load_param


def test_rcnn(network, dataset, image_set, root_path, dataset_path,
              ctx, prefix, epoch,
              vis, shuffle, has_rpn, proposal, thresh):
    # set config
    if has_rpn:
        config.TEST.HAS_RPN = True

    # print config
    pprint.pprint(config)

    # load symbol and testing data
    if has_rpn:
        sym = eval('get_' + network + '_test')(num_classes=config.NUM_CLASSES, num_anchors=config.NUM_ANCHORS)
        imdb = eval(dataset)(image_set, root_path, dataset_path)
        roidb = imdb.gt_roidb()
    else:
        sym = eval('get_' + network + '_rcnn_test')(num_classes=config.NUM_CLASSES)
        imdb = eval(dataset)(image_set, root_path, dataset_path)
        gt_roidb = imdb.gt_roidb()
        roidb = eval('imdb.' + proposal + '_roidb')(gt_roidb)

    # get test data iter
    test_data = TestLoader(roidb, batch_size=1, shuffle=shuffle, has_rpn=has_rpn)

    # load model
    arg_params, aux_params = load_param(prefix, epoch, convert=True, ctx=ctx, process=True)

    # check parameters
    param_names = [k for k in sym.list_arguments() + sym.list_auxiliary_states()
                   if k not in dict(test_data.provide_data) and 'label' not in k]
    missing_names = [k for k in param_names if k not in arg_params and k not in aux_params]
    if len(missing_names):
        print 'detected missing params', missing_names

    # decide maximum shape
    data_names = [k[0] for k in test_data.provide_data]
    label_names = ['cls_prob_label']
    max_data_shape = [('data', (1, 3, max([v[0] for v in config.SCALES]), max([v[1] for v in config.SCALES])))]
    if not has_rpn:
        max_data_shape.append(('rois', (1, config.TEST.PROPOSAL_POST_NMS_TOP_N + 30, 5)))
    predictor = Predictor(sym, data_names, label_names,
                          context=ctx, max_data_shapes=max_data_shape,
                          provide_data=test_data.provide_data, provide_label=test_data.provide_label,
                          arg_params=arg_params, aux_params=aux_params)

    # start detection
    pred_eval(predictor, test_data, imdb, vis=vis, thresh=thresh)


def parse_args():
    parser = argparse.ArgumentParser(description='Test a Fast R-CNN network')
    # general
    parser.add_argument('--network', help='network name', default=default.network, type=str)
    parser.add_argument('--dataset', help='dataset name', default=default.dataset, type=str)
    args, rest = parser.parse_known_args()
    generate_config(args.network, args.dataset)
    parser.add_argument('--image_set', help='image_set name', default=default.test_image_set, type=str)
    parser.add_argument('--root_path', help='output data folder', default=default.root_path, type=str)
    parser.add_argument('--dataset_path', help='dataset path', default=default.dataset_path, type=str)
    # testing
    parser.add_argument('--prefix', help='model to test with', default=default.rcnn_prefix, type=str)
    parser.add_argument('--epoch', help='model to test with', default=default.rcnn_epoch, type=int)
    parser.add_argument('--gpu', help='GPU device to test with', default=0, type=int)
    # rcnn
    parser.add_argument('--vis', help='turn on visualization', action='store_true')
    parser.add_argument('--thresh', help='valid detection threshold', default=1e-3, type=float)
    parser.add_argument('--shuffle', help='shuffle data on visualization', action='store_true')
    parser.add_argument('--has_rpn', help='generate proposals on the fly', action='store_true')
    parser.add_argument('--proposal', help='can be ss for selective search or rpn', default='rpn', type=str)
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    ctx = mx.gpu(args.gpu)
    print args
    test_rcnn(args.network, args.dataset, args.image_set, args.root_path, args.dataset_path,
              ctx, args.prefix, args.epoch,
              args.vis, args.shuffle, args.has_rpn, args.proposal, args.thresh)

if __name__ == '__main__':
    main()
