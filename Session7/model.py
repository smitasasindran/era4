# import torch
import torch.nn as nn
import torch.nn.functional as F


dropout_value = 0.1

#https://github.com/seungjunlee96/Depthwise-Separable-Convolution_Pytorch
def depthwise_separable_layer(nin, nout, dropout_value, padding=0):
    depthwise = nn.Conv2d(nin, nin, kernel_size=3, padding=padding, groups=nin, bias=False)
    pointwise = nn.Conv2d(nin, nout, kernel_size=1, bias=False)

    depthwise_separable = nn.Sequential(
        depthwise,
        nn.ReLU(),
        nn.BatchNorm2d(nin),
        nn.Dropout(dropout_value),
        pointwise,
        nn.ReLU(),
        nn.BatchNorm2d(nout),
        nn.Dropout(dropout_value)
    )
    return depthwise_separable


class Net(nn.Module):

    def __init__(self):
        super(Net, self).__init__()

        # Conv Block 1
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=16, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(16),
            nn.Dropout(dropout_value)
        ) # output_size = 32, rf=3

        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Dropout(dropout_value)
        ) # output_size = 32, rf=5

        self.conv3 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Dropout(dropout_value)
        ) # output_size = 32, rf=7

        # transition 1 - use stride2 instead of MP
        self.conv4 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 3), padding=0, stride=2, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(64),
            nn.Dropout(dropout_value)
        ) # output_size = 15, rf=9
        self.conv5 = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=16, kernel_size=(1, 1), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(16),
            nn.Dropout(dropout_value)
        ) # output_size = 15, rf=9

        # Conv Block 2 -------------------
        self.conv6 = nn.Sequential( # padding
            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Dropout(dropout_value)
        ) # output_size = 15, rf=13 (jump2)

        self.conv7 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Dropout(dropout_value)
        ) # output_size = 15, rf=17

        self.conv8 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(64),
            nn.Dropout(dropout_value)
        ) # output_size = 15, rf=21

        # Transition 2 --
        self.conv9 = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=16, kernel_size=(1, 1), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(16),
            nn.Dropout(dropout_value)
        ) # output_size = 15, rf=21


        # Conv Block 3 ---------------------
        self.conv10 = nn.Sequential( # padding
            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Dropout(dropout_value)
        ) # output_size = 15, rf=25

        self.conv11 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Dropout(dropout_value)
        ) # output_size = 13, rf=29

        # self.conv12 = nn.Sequential(
        #     nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
        #     nn.ReLU(),
        #     nn.BatchNorm2d(32),
        #     nn.Dropout(dropout_value)
        # ) # output_size = 11, rf=33
        self.conv12 = depthwise_separable_layer(32, 64, dropout_value, padding=0) # output_size=11, rf=33

        # transition 3
        self.conv13 = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=16, kernel_size=(1, 1), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(16),
            nn.Dropout(dropout_value)
        ) # output_size = 11, rf=33

        # Conv Block 4 - with dilation
        self.conv14 = nn.Sequential( # Dilation
            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), padding=0, dilation=2, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Dropout(dropout_value)
        ) # output_size = 7, rf=41 # dilation

        self.conv15 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
            nn.Dropout(dropout_value)
        ) # output_size = 5, rf=45

        # self.conv16 = nn.Sequential(
        #     nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 3), padding=0, bias=False),
        #     nn.ReLU(),
        #     nn.BatchNorm2d(64),
        #     nn.Dropout(dropout_value)
        # ) # output_size = 3


        # Output
        self.gap = nn.Sequential(
            nn.AvgPool2d(kernel_size=5)
        ) # output_size = 5

        self.conv17 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=10, kernel_size=(1, 1), padding=0, bias=False),
            # nn.BatchNorm2d(10),
            # nn.Dropout(dropout_value)
            # nn.ReLU()
        ) # output_size = 10, rf=45


    def forward(self, x):
        # block1
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x) # stride 2
        # print(f"conv4 out: {x.shape}")

        # block2
        x = self.conv5(x)
        x = self.conv6(x)
        x = self.conv7(x)
        x = self.conv8(x)

        # block3
        x = self.conv9(x)
        x = self.conv10(x)
        x = self.conv11(x)
        x = self.conv12(x)

        # block4
        x = self.conv13(x)
        x = self.conv14(x)
        x = self.conv15(x)
        # x = self.conv16(x)
        # print(f"conv15 out: {x.shape}")

        # Output
        x = self.gap(x)
        x = self.conv17(x)
        x = x.view(-1, 10)

        return F.log_softmax(x, dim=-1)

