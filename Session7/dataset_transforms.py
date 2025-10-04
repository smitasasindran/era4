import numpy as np
from torch.utils.data import Dataset
from torchvision import datasets, transforms
import albumentations as A
from albumentations.pytorch import ToTensorV2


class CIFAR10Albumentations(Dataset):
    def __init__(self, root, train=True, download=True, transform=None):
        self.cifar10 = datasets.CIFAR10(root=root, train=train, download=download)
        self.transform = transform

    def __len__(self):
        return len(self.cifar10)

    def __getitem__(self, idx):
        image, label = self.cifar10[idx]
        # Albumentations expects NumPy arrays, so convert PIL Image
        image = np.array(image)

        if self.transform:
            augmented = self.transform(image=image)
            image = augmented['image']

        return image, label


def create_transformations():
    # Train Phase transformations
    train_transforms = transforms.Compose([
        # A.HorizontalFlip(p=0.5),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.4914, 0.4822, 0.4465), std=(0.2470, 0.2435, 0.2616))
    ])

    # Test Phase transformations
    test_transforms = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.4914, 0.4822, 0.4465), std=(0.2470, 0.2435, 0.2616))
    ])
    return train_transforms, test_transforms


def create_albumentations_transforms():
    train_transforms = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.1, rotate_limit=10, p=0.5),
        # A.RandomBrightnessContrast(p=0.5),
        A.CoarseDropout(p=0.5, max_holes=1, max_height=16, max_width=16, min_holes=1, min_height=16, min_width=16,
                        fill_value=(0.4914, 0.4822, 0.4465), mask_fill_value=None), # CIFAR-10 mean as fill value
        A.Normalize(mean=(0.4914, 0.4822, 0.4465), std=(0.2471, 0.2435, 0.2616)),  # CIFAR-10 mean/std
        ToTensorV2(),
    ])

    test_transforms = A.Compose([
        A.Normalize(mean=(0.4914, 0.4822, 0.4465), std=(0.2471, 0.2435, 0.2616)),
        ToTensorV2(),
    ])

    return train_transforms, test_transforms


def load_dataset(train_transforms, test_transforms):
    train = datasets.CIFAR10('./data', train=True, download=True, transform=train_transforms)
    test = datasets.CIFAR10('./data', train=False, download=True, transform=test_transforms)
    return train, test


def load_albumentations_dataset(train_transforms, test_transforms):
    train = CIFAR10Albumentations(root='./data', train=True, download=True, transform=train_transforms)
    test = CIFAR10Albumentations(root='./data', train=False, download=True, transform=test_transforms)
    return train, test