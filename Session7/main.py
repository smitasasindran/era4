from __future__ import print_function
import torch
import torch.optim as optim

import utils
import dataset_transforms
from model import Net


if __name__ == "__main__":
    use_albumentations = False

    if use_albumentations:
        # Create albumentations transforms
        train_transforms, test_transforms = dataset_transforms.create_albumentations_transforms()

        # Load dataset with albumentations
        train, test = dataset_transforms.load_albumentations_dataset(train_transforms, test_transforms)
    else:
        # Create torch transforms
        train_transforms, test_transforms = dataset_transforms.create_transformations()

        # Load dataset
        train, test = dataset_transforms.load_dataset(train_transforms, test_transforms)

    # Set random seed and batch size
    use_cuda = utils.init_setup()
    batch_size = 512  # 256

    # Create data loaders
    train_loader, test_loader = utils.get_dataloaders(train, test, use_cuda, batch_size)

    device = torch.device("cuda" if use_cuda else "cpu")
    # print(device)
    model_cifar = Net().to(device)
    utils.model_summary(model_cifar)

    # Train and test accumulator variables
    train_losses = []
    test_losses = []
    train_acc = []
    test_acc = []

    # Training and test loop
    model_cifar = Net().to(device)
    optimizer = optim.SGD(model_cifar.parameters(), lr=0.01, momentum=0.9)
    EPOCHS = 100
    for epoch in range(EPOCHS):
        print("EPOCH:", epoch)
        utils.train(model_cifar, device, train_loader, optimizer, epoch, train_losses, train_acc)
        utils.test(model_cifar, device, test_loader, test_losses, test_acc)

    # Plot the graphs
    ## For colab, uncomment this:
    # % matplotlib inline
    utils.plot_graphs(train_losses, train_acc, test_losses, test_acc)

