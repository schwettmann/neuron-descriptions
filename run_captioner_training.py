"""Train a neuron captioner from scratch."""
import argparse
import pathlib

from lv import zoo
from lv.models import decoders, encoders, lms

DATASETS = (
    zoo.KEY_ALEXNET_IMAGENET,
    zoo.KEY_ALEXNET_PLACES365,
    zoo.KEY_RESNET152_IMAGENET,
    zoo.KEY_RESNET152_PLACES365,
    zoo.KEY_BIGGAN_IMAGENET,
    zoo.KEY_BIGGAN_PLACES365,
)

ENCODER_RESNET18 = 'resnet18'
ENCODER_RESNET50 = 'resnet50'
ENCODERS = (ENCODER_RESNET18, ENCODER_RESNET50)

parser = argparse.ArgumentParser(description='train a captioner')
parser.add_argument(
    '--out-file',
    type=pathlib.Path,
    help='save model to this file (default: ./<generated name>)')
parser.add_argument('--datasets',
                    nargs='+',
                    default=DATASETS,
                    help='datasets to train on (default: all)')
parser.add_argument('--encoder',
                    choices=ENCODERS,
                    default=ENCODER_RESNET50,
                    help='image encoder (default: resnet50)')
parser.add_argument('--no-lm',
                    action='store_true',
                    help='do not train lm (default: train lm)')
parser.add_argument('--precompute-features',
                    action='store_true',
                    help='precompute image features (default: do not)')
parser.add_argument(
    '--hold-out',
    type=float,
    default=.1,
    help='hold out and validate on this fraction of training data '
    '(default: .1)')
parser.add_argument('--cuda',
                    action='store_true',
                    help='use cuda device (default: cpu)')
args = parser.parse_args()

device = 'cuda' if args.cuda else 'cpu'

dataset = zoo.datasets(*args.datasets)

lm = None
if not args.no_lm:
    lm = lms.lm(dataset)
    lm.fit(dataset, device=device)

encoder = encoders.PyramidConvEncoder(config=args.encoder)

features = None
if args.precompute_features:
    features = encoder.map(dataset, device=device)

decoder = decoders.decoder(dataset, encoder)
decoder.fit(dataset, features=features, device=device)

out_file = args.out_file
if not out_file:
    out_file = f'cap+{args.encoder}{"" if args.no_lm else "+lm"}.pth'

decoder.save(out_file)
