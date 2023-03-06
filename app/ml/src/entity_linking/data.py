import cv2
import torch
import albumentations as A
from albumentations.pytorch import ToTensorV2
from torch.utils.data import Dataset, DataLoader
import traceback   
import h5py

import logging
import logging.config
from yaml import safe_load
with open('../conf/logging.yml') as f:
    cfg = safe_load(f)
logging.config.dictConfig(cfg)
logger = logging.getLogger('data')
    

def GetTransforms(input_size, color_mean = [0.485, 0.456, 0.406], color_std = [0.229, 0.224, 0.225]):
    data_transforms = {
        "train": A.Compose([
            A.HorizontalFlip(p=0.5),
            A.ImageCompression(quality_lower=99, quality_upper=100),
            A.ShiftScaleRotate(shift_limit=0.2, scale_limit=0.2, rotate_limit=10, border_mode=0, p=0.7),
            A.Resize(input_size, input_size),
            A.Cutout(max_h_size=int(input_size * 0.4), max_w_size=int(input_size * 0.4), num_holes=1, p=0.5),
            A.Normalize(mean=color_mean, std=color_std, max_pixel_value=255.0, p=1.0),
            ToTensorV2()], p=1.),
        
        "val": A.Compose([
            A.Resize(input_size, input_size),
            A.Normalize(mean=color_mean, std=color_std, max_pixel_value=255.0, p=1.0),
            ToTensorV2()], p=1.)
    }
    
    return data_transforms

class EntityLinkingDataset(Dataset):
    def __init__(self, path_h5, transforms=None):
        logger.info(f"Loading {path_h5}")
        self.h5 = h5py.File(path_h5,'r')
        assert self.h5, f"Cannot find {path_h5}"
        self.h5_path = self.h5['path']
        self.h5_label = self.h5['label']
        self.h5_img = self.h5['img']
        self.transforms = transforms
        
    def __len__(self):
        return len(self.h5_label)
    
    def __getitem__(self, idx):
      try:
        path = self.h5_path[str(idx)][0]
        label = self.h5_label[str(idx)][0]
        img = self.h5_img[str(idx)][0]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        if self.transforms:
            img = self.transforms(image=img)["image"]
            
        return {
            'image': img,
            'path': path,
            'label': torch.tensor(label, dtype=torch.long),
        }
      except Exception: 
        traceback.print_exc()
        logger.info(f"path: {path}")
        return None

def collate_fn(batch):
    batch = list(filter(lambda x: x is not None, batch))
    return torch.utils.data.dataloader.default_collate(batch)

def prepare_loaders(path_h5, transforms, batch_size, is_train=True, fold=0):
    # assert not df.empty
    # logger.info(f'len(df) = {len(df)}')
    assert transforms["train"]
    assert transforms["val"]
    assert batch_size["train"]
    assert batch_size["val"]
    assert 0 <= fold <= 4
    if is_train:
        datasets = {
            x: EntityLinkingDataset(path_h5[x], transforms=transforms[x])
            for x in ["train", "val"]
        }
        dataloaders = {
            x: DataLoader(datasets[x], batch_size=batch_size[x], num_workers=2, collate_fn = collate_fn, shuffle=True, pin_memory=True, drop_last=True)
            for x in ["train", "val"]
        }
        assert len(dataloaders['train']) > 0, f"len(dataloaders['train']: {len(dataloaders['train'])}"
        assert len(dataloaders['val']) > 0, f"len(dataloaders['val']: {len(dataloaders['val'])}"
        logger.info(f"len(dataloaders['train']): {len(dataloaders['train'])}")
        logger.info(f"len(dataloaders['val']): {len(dataloaders['val'])}")
        return dataloaders
    else:
        dataset = EntityLinkingDataset(path_h5["test"], transforms=transforms["val"])
        dataloader = DataLoader(dataset, batch_size=batch_size["val"], num_workers=2, collate_fn = collate_fn, shuffle=True, pin_memory=True, drop_last=True)
        assert len(dataloader) > 0, f"len(dataloader: {len(dataloader)}"
        logger.info(f"len(dataloader): {len(dataloader)}")
        return dataloader
  
    

# def prepare_loaders(df, transforms, batch_size, is_train=True, fold=0):
#     assert not df.empty
#     logger.info(f'len(df) = {len(df)}')
#     assert transforms["train"]
#     assert transforms["val"]
#     assert batch_size["train"]
#     assert batch_size["val"]
#     assert 0 <= fold <= 4
    
#     if is_train:
#         df_train_val = {
#             "train": df[df.kfold != fold].reset_index(drop=True),
#             "val": df[df.kfold == fold].reset_index(drop=True)
#         }

#         assert not df_train_val["train"].empty
#         assert not df_train_val["val"].empty

#         logger.info(f'len(df_train_val["train"]) = {len(df_train_val["train"])}')
#         logger.info(f'len(df_train_val["val"]) = {len(df_train_val["val"])}')
        
#         datasets = {
#             x: EntityLinkingDataset(df_train_val[x], transforms=transforms[x])
#             for x in ["train", "val"]
#         }
#         dataloaders = {
#             x: DataLoader(datasets[x], batch_size=batch_size[x], num_workers=2, collate_fn = collate_fn, shuffle=True, pin_memory=True, drop_last=True)
#             for x in ["train", "val"]
#         }
#         assert len(dataloaders['train']) > 0, f"len(dataloaders['train']: {len(dataloaders['train'])}"
#         assert len(dataloaders['val']) > 0, f"len(dataloaders['val']: {len(dataloaders['val'])}"
#         logger.info(f"len(dataloaders['train']): {len(dataloaders['train'])}")
#         logger.info(f"len(dataloaders['val']): {len(dataloaders['val'])}")
#     else:
#         datasets = {
#             x: EntityLinkingDataset(df, transforms=transforms[x])
#             for x in ["val"]
#         }
#         dataloaders = {
#             x: DataLoader(datasets[x], batch_size=batch_size[x], num_workers=2, collate_fn = collate_fn, shuffle=True, pin_memory=True, drop_last=True)
#             for x in ["val"]
#         }
#         assert len(dataloaders['val']) > 0, f"len(dataloaders['val']: {len(dataloaders['val'])}"
#         logger.info(f"len(dataloaders['val']): {len(dataloaders['val'])}")
  
#     return dataloaders

# class EntityLinkingDataset(Dataset):
#     def __init__(self, df, transforms=None):
#         self.df = df
#         self.file_paths = df['path'].values
#         # self.file_noncrop_paths = df['path_noncrop'].values
#         self.file_names = df['file_name'].values
#         self.ids = df['wikidata_id'].values
#         self.labels = df['label'].values
#         self.transforms = transforms
        
#     def __len__(self):
#         return len(self.df)
    
#     def __getitem__(self, index):
#       try:
#         file_path = self.file_paths[index]
#         # file_noncrop_path = self.file_noncrop_paths[index]
#         label = self.labels[index]
#         file_name = self.file_names[index]
#         wikidata_id = self.ids[index]

#         img = cv2.imread(file_path)
#         img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
#         if self.transforms:
#             img = self.transforms(image=img)["image"]
            
#         return {
#             'image': img,
#             'file_path': file_path,
#             # 'file_noncrop_path': file_noncrop_path,
#             'label': torch.tensor(label, dtype=torch.long),
#             'file_name': file_name,
#             'wikidata_id': wikidata_id,
#         }
#       except Exception: 
#         logger.info(f"file_path: {file_path}")
#         traceback.print_exc()
#         return None