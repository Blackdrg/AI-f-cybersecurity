#!/usr/bin/env python3
import argparse, logging, sys
from pathlib import Path
import numpy as np
import onnx
import onnxruntime as ort
import torch
import torch.nn as nn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_arcface(output_path):
    class M(nn.Module):
        def __init__(s):
            super().__init__()
            s.conv1 = nn.Conv2d(3,64,7,stride=2,padding=3)
            s.bn1 = nn.BatchNorm2d(64)
            s.relu = nn.ReLU(inplace=True)
            s.maxpool = nn.MaxPool2d(3,stride=2,padding=1)
            s.layer1 = nn.Sequential(nn.Conv2d(64,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU(inplace=True),nn.Conv2d(64,256,3,padding=1),nn.BatchNorm2d(256))
            s.avgpool = nn.AdaptiveAvgPool2d((1,1))
            s.fc = nn.Linear(256,512)
        def forward(s,x):
            x = s.conv1(x)
            x = s.bn1(x)
            x = s.relu(x)
            x = s.maxpool(x)
            x = s.layer1(x)
            x = s.avgpool(x)
            return s.fc(torch.flatten(x,1))
    m = M().eval()
    torch.onnx.export(m,torch.randn(1,3,112,112),str(output_path),export_params=True,opset_version=14,input_names=['input'],output_names=['embedding'],dynamic_axes={'input':{0:'batch'},'embedding':{0:'batch'}})
    onnx_model = onnx.load(str(output_path))
    onnx.checker.check_model(onnx_model)
    return output_path

def create_xceptionnet(output_path):
    class DWS(nn.Module):
        def __init__(s,in_c,out_c,stride=1):
            super().__init__()
            s.c = nn.Sequential(nn.Conv2d(in_c,in_c,3,stride=stride,padding=1,groups=in_c),nn.Conv2d(in_c,out_c,1),nn.BatchNorm2d(out_c),nn.ReLU(inplace=True))
        def forward(s,x):
            return s.c(x)
    class M(nn.Module):
        def __init__(s):
            super().__init__()
            s.net = nn.Sequential(DWS(3,64),DWS(64,128,2),DWS(128,256,2),nn.AdaptiveAvgPool2d((1,1)),nn.Flatten(),nn.Linear(256,2))
        def forward(s,x):
            return s.net(x)
    m = M().eval()
    torch.onnx.export(m,torch.randn(1,3,224,224),str(output_path),export_params=True,opset_version=14,input_names=['input'],output_names=['spoof_score'])
    onnx_model = onnx.load(str(output_path))
    onnx.checker.check_model(onnx_model)
    return output_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker',action='store_true')
    parser.add_argument('--output-dir',type=str,default=None)
    parser.add_argument('--models',type=str,nargs='+',default=['arcface_resnet100','xceptionnet'])
    args = parser.parse_args()
    out_dir = Path('/models/onnx_bundle' if args.docker else args.output_dir or Path(__file__).parent/'onnx_bundle')
    out_dir.mkdir(parents=True,exist_ok=True)
    logger.info(f'Output: {out_dir}')
    map = {'arcface_resnet100':('insightface_buffalo_l.onnx',create_arcface),'xceptionnet':('xceptionnet_spoof_detector.onnx',create_xceptionnet)}
    results = {}
    for name in args.models:
        try:
            fname,creator = map[name]
            path = out_dir/fname
            if not path.exists():
                creator(path)
            sess = ort.InferenceSession(str(path),providers=['CPUExecutionProvider'])
            inp = sess.get_inputs()[0]
            ishp = [1 if isinstance(d,str) else d for d in inp.shape]
            dummy = np.random.randn(*ishp).astype(np.float32)
            sess.run(None,{inp.name:dummy})
            results[name] = 'OK'
            logger.info(f'OK: {name}')
        except Exception as e:
            logger.error(f'ERROR {name}: {e}')
            results[name] = f'ERROR: {e}'
    print('\n'+'='*60+'\nSummary\n'+'='*60)
    for n,s in results.items():
        print(f'  {n:40s} {s}')
    print('='*60)
    sys.exit(0 if all('OK' in str(s) for s in results.values()) else 1)

if __name__ == '__main__':
    main()
