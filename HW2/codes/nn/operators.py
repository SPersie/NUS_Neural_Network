import numpy as np

from utils.tools import *
from nn.functional import sigmoid, img2col
# Attension:
# - Never change the value of input, which will change the result of backward


class operator(object):
    """
    operator abstraction
    """

    def forward(self, input):
        """Forward operation, reture output"""
        raise NotImplementedError

    def backward(self, out_grad, input):
        """Backward operation, return gradient to input"""
        raise NotImplementedError


class relu(operator):
    def __init__(self):
        super(relu, self).__init__()

    def forward(self, input):
        output = np.maximum(0, input)
        return output

    def backward(self, out_grad, input):
        in_grad = (input >= 0) * out_grad
        return in_grad


class flatten(operator):
    def __init__(self):
        super(flatten, self).__init__()

    def forward(self, input):
        batch = input.shape[0]
        output = input.copy().reshape(batch, -1)
        return output

    def backward(self, out_grad, input):
        in_grad = out_grad.copy().reshape(input.shape)
        return in_grad


class matmul(operator):
    def __init__(self):
        super(matmul, self).__init__()

    def forward(self, input, weights):
        """
        # Arguments
            input: numpy array with shape (batch, in_features)
            weights: numpy array with shape (in_features, out_features)

        # Returns
            output: numpy array with shape(batch, out_features)
        """
        return np.matmul(input, weights)

    def backward(self, out_grad, input, weights):
        """
        # Arguments
            out_grad: gradient to the forward output of linear layer, with shape (batch, out_features)
            input: numpy array with shape (batch, in_features)
            weights: numpy array with shape (in_features, out_features)

        # Returns
            in_grad: gradient to the forward input with same shape as input
            w_grad: gradient to weights, with same shape as weights            
        """
        in_grad = np.matmul(out_grad, weights.T)
        w_grad = np.matmul(input.T, out_grad)
        return in_grad, w_grad


class add_bias(operator):
    def __init__(self):
        super(add_bias, self).__init__()

    def forward(self, input, bias):
        '''
        # Arugments
          input: numpy array with shape (batch, in_features)
          bias: numpy array with shape (in_features)

        # Returns
          output: numpy array with shape(batch, in_features)
        '''
        return input + bias.reshape(1, -1)

    def backward(self, out_grad, input, bias):
        """
        # Arguments
            out_grad: gradient to the forward output of linear layer, with shape (batch, out_features)
            input: numpy array with shape (batch, in_features)
            bias: numpy array with shape (out_features)
        # Returns
            in_grad: gradient to the forward input with same shape as input
            b_bias: gradient to bias, with same shape as bias
        """
        in_grad = out_grad
        b_grad = np.sum(out_grad, axis=0)
        return in_grad, b_grad


class linear(operator):
    def __init__(self):
        super(linear, self).__init__()
        self.matmul = matmul()
        self.add_bias = add_bias()

    def forward(self, input, weights, bias):
        """
        # Arguments
            input: numpy array with shape (batch, in_features)
            weights: numpy array with shape (in_features, out_features)
            bias: numpy array with shape (out_features)

        # Returns
            output: numpy array with shape(batch, out_features)
        """
        output = self.matmul.forward(input, weights)
        output = self.add_bias.forward(output, bias)
        # output = np.matmul(input, weights) + bias.reshape(1, -1)
        return output

    def backward(self, out_grad, input, weights, bias):
        """
        # Arguments
            out_grad: gradient to the forward output of linear layer, with shape (batch, out_features)
            input: numpy array with shape (batch, in_features)
            weights: numpy array with shape (in_features, out_features)
            bias: numpy array with shape (out_features)

        # Returns
            in_grad: gradient to the forward input of linear layer, with same shape as input
            w_grad: gradient to weights, with same shape as weights
            b_bias: gradient to bias, with same shape as bias
        """
        # in_grad = np.matmul(out_grad, weights.T)
        # w_grad = np.matmul(input.T, out_grad)
        # b_grad = np.sum(out_grad, axis=0)
        out_grad, b_grad = self.add_bias.backward(out_grad, input, bias)
        in_grad, w_grad = self.matmul.backward(out_grad, input, weights)
        return in_grad, w_grad, b_grad


class conv(operator):
    def __init__(self, conv_params):
        """
        # Arguments
            conv_params: dictionary, containing these parameters:
                'kernel_h': The height of kernel.
                'kernel_w': The width of kernel.
                'stride': The number of pixels between adjacent receptive fields in the horizontal and vertical directions.
                'pad': The total number of 0s to be added along the height (or width) dimension; half of the 0s are added on the top (or left) and half at the bottom (or right). we will only test even numbers.
                'in_channel': The number of input channels.
                'out_channel': The number of output channels.
        """
        super(conv, self).__init__()
        self.conv_params = conv_params
        self.matmul = matmul()
        self.add_bias = add_bias()

    def forward(self, input, weights, bias):
        """
        # Arguments
            input: numpy array with shape (batch, in_channel, in_height, in_width)
            weights: numpy array with shape (out_channel, in_channel, kernel_h, kernel_w)
            bias: numpy array with shape (out_channel)

        # Returns
            output: numpy array with shape (batch, out_channel, out_height, out_width)
        """
        kernel_h = self.conv_params['kernel_h']  # height of kernel
        kernel_w = self.conv_params['kernel_w']  # width of kernel
        pad = self.conv_params['pad']
        stride = self.conv_params['stride']
        in_channel = self.conv_params['in_channel']
        out_channel = self.conv_params['out_channel']

        batch, in_channel, in_height, in_width = input.shape
        #####################################################################################
        # code here
        opt_h = int(((in_height - kernel_h + pad) / stride) + 1)
        opt_w = int(((in_width - kernel_w + pad) / stride) + 1)

        # add padding to input
        pad_scheme = (pad//2, pad - pad//2)
        input_pad = np.pad(input, pad_width=((0,0), (0,0), pad_scheme, pad_scheme),
                           mode='constant', constant_values=0)

        recep_fields_h = [stride*i for i in range(opt_h)]
        recep_fields_w = [stride*i for i in range(opt_w)]

        input_pool = img2col(input_pad, recep_fields_h,
                             recep_fields_w, kernel_h, kernel_w)

        weight_h = np.reshape(weights, (out_channel, in_channel * kernel_h * kernel_w))

        # initialize outtput
        output = np.zeros((batch, out_channel, opt_h * opt_w))
        bias_h = np.zeros((out_channel, opt_h * opt_w))

        for i in range(out_channel):
            for j in range(opt_h * opt_w):
                bias_h[i][j] = bias[i]

        for i in range(batch):
            output[i] = np.matmul(weight_h, input_pool[i])  + bias_h
    
        # print(bias.shape)
        # print(input_pool.shape)
        # print(weight_h.shape)
        
        output = output.reshape(batch, out_channel, opt_h, opt_w)
        
        #####################################################################################
        return output

    def backward(self, out_grad, input, weights, bias):
        """
        # Arguments
            out_grad: gradient to the forward output of conv layer, with shape (batch, out_channel, out_height, out_width)
            input: numpy array with shape (batch, in_channel, in_height, in_width)
            weights: numpy array with shape (out_channel, in_channel, kernel_h, kernel_w)
            bias: numpy array with shape (out_channel)

        # Returns
            in_grad: gradient to the forward input of conv layer, with same shape as input
            w_grad: gradient to weights, with same shape as weights
            b_bias: gradient to bias, with same shape as bias
        """
        kernel_h = self.conv_params['kernel_h']  # height of kernel
        kernel_w = self.conv_params['kernel_w']  # width of kernel
        pad = self.conv_params['pad']
        stride = self.conv_params['stride']
        in_channel = self.conv_params['in_channel']
        out_channel = self.conv_params['out_channel']
        
        
        
        batch, in_channel, in_height, in_width = input.shape
        #################################################################################
        # code here
        opt_h = int(((in_height - kernel_h + pad) / stride) + 1)
        opt_w = int(((in_width - kernel_w + pad) / stride) + 1)

        in_grad = np.zeros((batch, in_channel, in_height + 2 * pad, in_width + 2 * pad))
        # add padding to input
        pad_scheme = (pad//2, pad - pad//2)
        input_pad = np.pad(input, pad_width=((0,0), (0,0), pad_scheme, pad_scheme),
                           mode='constant', constant_values=0)

        recep_fields_h = [stride*i for i in range(opt_h)]
        recep_fields_w = [stride*i for i in range(opt_w)]

        input_pool = img2col(input_pad, recep_fields_h,
                             recep_fields_w, kernel_h, kernel_w)
        input_pool_grad = np.stack(map(lambda x: np.matmul(weights.reshape(out_channel, -1).T, x),
                                    out_grad.reshape(batch, out_channel, -1)), axis=0)

        flag = 0
        for h in recep_fields_h:
            for w in recep_fields_w:
                grad = input_pool_grad[:,:,flag].reshape(batch, in_channel, kernel_h, kernel_w)
                in_grad[:,:,h:h+kernel_h, w:w+kernel_w] += grad
                flag += 1


        in_grad = in_grad[:, :, pad:pad+in_height, pad:pad+in_width]
        w_grad = sum(list(map(lambda x: np.matmul(x[0], x[1].T),
                                zip(out_grad.reshape(batch, out_channel, -1), input_pool)))) \
                    .reshape(weights.shape)  
        b_grad = out_grad.sum(axis=(0, 2, 3))
        #################################################################################
        return in_grad, w_grad, b_grad


class pool(operator):
    def __init__(self, pool_params):
        """
        # Arguments
            pool_params: dictionary, containing these parameters:
                'pool_type': The type of pooling, 'max' or 'avg'
                'pool_h': The height of pooling kernel.
                'pool_w': The width of pooling kernel.
                'stride': The number of pixels between adjacent receptive fields in the horizontal and vertical directions.
                'pad': The total number of 0s to be added along the height (or width) dimension; half of the 0s are added on the top (or left) and half at the bottom (or right). we will only test even numbers.
        """
        super(pool, self).__init__()
        self.pool_params = pool_params

    def forward(self, input):
        """
        # Arguments
            input: numpy array with shape (batch, in_channel, in_height, in_width)

        # Returns
            output: numpy array with shape (batch, in_channel, out_height, out_width)
        """
        pool_type = self.pool_params['pool_type']
        pool_height = self.pool_params['pool_height']
        pool_width = self.pool_params['pool_width']
        stride = self.pool_params['stride']
        pad = self.pool_params['pad']

        batch, in_channel, in_height, in_width = input.shape
        #####################################################################################
        # code here
        opt_h = int(((in_height - pool_height + pad) / stride) + 1)
        opt_w = int(((in_width - pool_width + pad) / stride) + 1)

        # add padding to input
        pad_scheme = (pad//2, pad - pad//2)
        input_pad = np.pad(input, pad_width=((0,0), (0,0), pad_scheme, pad_scheme),
                           mode='constant', constant_values=0)

        output = np.zeros((batch, in_channel, opt_h, opt_w, pool_height, pool_width))

        for h in range(opt_h):
            for w in range(opt_w):
                grad = input_pad[:,:,(h*stride):(h*stride+pool_height),
                                    (w*stride):(w*stride+pool_width)]
                output[:,:,h,w] += grad
        if pool_type == 'max':
            output = np.max(output, axis=(4,5))
        else:
            output = np.mean(output, axis=(4,5))

        #####################################################################################
        return output

    def backward(self, out_grad, input):
        """
        # Arguments
            out_grad: gradient to the forward output of conv layer, with shape (batch, in_channel, out_height, out_width)
            input: numpy array with shape (batch, in_channel, in_height, in_width)

        # Returns
            in_grad: gradient to the forward input of pool layer, with same shape as input
        """
        pool_type = self.pool_params['pool_type']
        pool_height = self.pool_params['pool_height']
        pool_width = self.pool_params['pool_width']
        stride = self.pool_params['stride']
        pad = self.pool_params['pad']

        batch, in_channel, in_height, in_width = input.shape
        out_height = 1 + (in_height - pool_height + pad) // stride
        out_width = 1 + (in_width - pool_width + pad) // stride

        pad_scheme = (pad//2, pad - pad//2)
        input_pad = np.pad(input, pad_width=((0,0), (0,0), pad_scheme, pad_scheme),
                           mode='constant', constant_values=0)

        recep_fields_h = [stride*i for i in range(out_height)]
        recep_fields_w = [stride*i for i in range(out_width)]

        input_pool = img2col(input_pad, recep_fields_h,
                             recep_fields_w, pool_height, pool_width)
        input_pool = input_pool.reshape(
            batch, in_channel, -1, out_height, out_width)

        if pool_type == 'max':
            input_pool_grad = (input_pool == np.max(input_pool, axis=2, keepdims=True)) * \
                out_grad[:, :, np.newaxis, :, :]

        elif pool_type == 'avg':
            scale = 1 / (pool_height*pool_width)
            input_pool_grad = scale * \
                np.repeat(out_grad[:, :, np.newaxis, :, :],
                          pool_height*pool_width, axis=2)

        input_pool_grad = input_pool_grad.reshape(
            batch, in_channel, -1, out_height*out_width)

        input_pad_grad = np.zeros(input_pad.shape)
        idx = 0
        for i in recep_fields_h:
            for j in recep_fields_w:
                input_pad_grad[:, :, i:i+pool_height, j:j+pool_width] += \
                    input_pool_grad[:, :, :, idx].reshape(
                        batch, in_channel, pool_height, pool_width)
                idx += 1
        in_grad = input_pad_grad[:, :, pad:pad+in_height, pad:pad+in_width]
        return in_grad


class dropout(operator):
    def __init__(self, rate, training=True, seed=None):
        """
        # Arguments
            rate: float[0, 1], the probability of setting a neuron to zero
            training: boolean, apply this layer for training or not. If for training, randomly drop neurons, else DO NOT drop any neurons
            seed: int, random seed to sample from input, so as to get mask, which is convenient to check gradients. But for real training, it should be None to make sure to randomly drop neurons
            mask: the mask with value 0 or 1, corresponding to drop neurons (0) or not (1). same shape as input
        """
        self.rate = rate
        self.seed = seed
        self.training = training
        self.mask = None

    def forward(self, input):
        """
        # Arguments
            input: numpy array with any shape

        # Returns
            output: same shape as input
        """
        if self.training:
            scale = 1/(1-self.rate)
            np.random.seed(self.seed)
            p = np.random.random_sample(input.shape)
            # Please use p as the probability to decide whether drop or not
            self.mask = (p >= self.rate).astype('int')
            #####################################################################################
            # code here
            output = self.mask * input * scale
            #####################################################################################
        else:
            output = input
        return output

    def backward(self, out_grad, input):
        """
        # Arguments
            out_grad: gradient to forward output of dropout, same shape as input
            input: numpy array with any shape
            mask: the mask with value 0 or 1, corresponding to drop neurons (0) or not (1). same shape as input

        # Returns
            in_grad: gradient to forward input of dropout, same shape as input
        """
        if self.training:
            #####################################################################################
            # code here
            scale = 1/(1-self.rate)
            in_grad = out_grad * self.mask * scale
            #####################################################################################
        else:
            in_grad = out_grad
        return in_grad


class vanilla_rnn(operator):
    def __init__(self):
        """
        # Arguments
            in_features: int, the number of inputs features
            units: int, the number of hidden units
            initializer: Initializer class, to initialize weights
        """
        super(vanilla_rnn, self).__init__()

    def forward(self, input, kernel, recurrent_kernel, bias):
        """
        # Arguments
            inputs: [input numpy array with shape (batch, in_features), 
                    state numpy array with shape (batch, units)]

        # Returns
            outputs: numpy array with shape (batch, units)
        """
        x, prev_h = input
        output = np.tanh(x.dot(kernel) + prev_h.dot(recurrent_kernel) + bias)
        return output

    def backward(self, out_grad, input, kernel, recurrent_kernel, bias):
        """
        # Arguments
            in_grads: numpy array with shape (batch, units), gradients to outputs
            inputs: [input numpy array with shape (batch, in_features), 
                    state numpy array with shape (batch, units)], same with forward inputs

        # Returns
            out_grads: [gradients to input numpy array with shape (batch, in_features), 
                        gradients to state numpy array with shape (batch, units)]
        """
        x, prev_h = input
        tanh_grad = np.nan_to_num(
            out_grad*(1-np.square(self.forward(input, kernel, recurrent_kernel, bias))))

        in_grad = [np.matmul(tanh_grad, kernel.T), np.matmul(
            tanh_grad, recurrent_kernel.T)]
        kernel_grad = np.matmul(np.nan_to_num(x.T), tanh_grad)
        r_kernel_grad = np.matmul(np.nan_to_num(prev_h.T), tanh_grad)
        b_grad = np.sum(tanh_grad, axis=0)

        return in_grad, kernel_grad, r_kernel_grad, b_grad


class gru(operator):
    def __init__(self):
        """
        # Arguments
            in_features: int, the number of inputs features
            units: int, the number of hidden units
            initializer: Initializer class, to initialize weights
        """
        super(gru, self).__init__()

    def forward(self, input, kernel, recurrent_kernel):
        """
        # Arguments
            inputs: [input numpy array with shape (batch, in_features), 
                    state numpy array with shape (batch, units)]

        # Returns
            outputs: numpy array with shape (batch, units)
        """
        x, prev_h = input
        _, all_units = kernel.shape
        units = all_units // 3
        kernel_z, kernel_r, kernel_h = kernel[:, :units], kernel[:, units:2*units],  kernel[:, 2*units:all_units]
        recurrent_kernel_z = recurrent_kernel[:, :units]
        recurrent_kernel_r = recurrent_kernel[:, units:2*units]
        recurrent_kernel_h = recurrent_kernel[:, 2*units:all_units]

        #####################################################################################
        # code here
        # reset gate
        x_r = sigmoid(np.dot(prev_h, recurrent_kernel_r) + np.dot(x, kernel_r))
        # update gate
        x_z = sigmoid(np.dot(prev_h, recurrent_kernel_z) + np.dot(x, kernel_z))
        # new gate
        x_h = np.tanh(np.dot(x_r * prev_h, recurrent_kernel_h) + np.dot(x, kernel_h))
        #####################################################################################

        output = (1 - x_z) * x_h + x_z * prev_h
        
        return output

    def backward(self, out_grad, input, kernel, recurrent_kernel):
        """
        # Arguments
            in_grads: numpy array with shape (batch, units), gradients to outputs
            inputs: [input numpy array with shape (batch, in_features), 
                    state numpy array with shape (batch, units)], same with forward inputs

        # Returns
            out_grads: [gradients to input numpy array with shape (batch, in_features), 
                        gradients to state numpy array with shape (batch, units)]
        """
        x, prev_h = input
        _, all_units = kernel.shape
        units = all_units // 3
        kernel_z, kernel_r, kernel_h = kernel[:, :units], kernel[:, units:2*units],  kernel[:, 2*units:all_units]
        recurrent_kernel_z = recurrent_kernel[:, :units]
        recurrent_kernel_r = recurrent_kernel[:, units:2*units]
        recurrent_kernel_h = recurrent_kernel[:, 2*units:all_units]

        #####################################################################################
        # code here
        # https://towardsdatascience.com/forward-and-backpropagation-in-grus-derived-deep-learning-5764f374f3f5
        
        zt = sigmoid(np.dot(prev_h, recurrent_kernel_z) + np.dot(x, kernel_z))
        rt = sigmoid(np.dot(prev_h, recurrent_kernel_r) + np.dot(x, kernel_r))
        h_hat = np.tanh(np.dot(rt*prev_h, recurrent_kernel_h) + np.dot(x, kernel_h))

        d0 = out_grad
        d1 = d0 * zt
        d2 = d0 * prev_h
        d3 = d0 * h_hat
        d4 = -1 * d3
        d5 = d2 + d4
        d6 = d0 * (1- zt)
        d7 = d5 * (zt * (1 - zt))
        d8 = d6 * (1 - h_hat**2)
        d9 = np.dot(d8, kernel_h.T)
        d10 = np.dot(d8, recurrent_kernel_h.T)
        d11 = np.dot(d7, kernel_z.T)
        d12 = np.dot(d7, recurrent_kernel_z.T)
        d14 = d10 * rt
        d15 = d10 * prev_h
        d16 = d15 * (rt * (1 - rt))
        d13 = np.dot(d16, kernel_r.T)
        d17 = np.dot(d16, recurrent_kernel_r.T)

        x_grad = np.nan_to_num(d9 + d11 + d13)
        prev_h_grad = np.nan_to_num(d12 + d14 + d1 + d17)

        kernel_r_grad = np.nan_to_num(np.dot(x.T, d16))
        kernel_z_grad = np.nan_to_num(np.dot(x.T, d7))
        kernel_h_grad = np.nan_to_num(np.dot(x.T, d8))

        recurrent_kernel_r_grad = np.nan_to_num(np.dot(prev_h.T, d16))
        recurrent_kernel_z_grad = np.nan_to_num(np.dot(prev_h.T, d7))
        recurrent_kernel_h_grad = np.nan_to_num(np.dot((rt*prev_h).T, d8))
        #####################################################################################

        in_grad = [x_grad, prev_h_grad]
        kernel_grad = np.concatenate([kernel_z_grad, kernel_r_grad, kernel_h_grad], axis=-1)
        r_kernel_grad = np.concatenate([recurrent_kernel_z_grad, recurrent_kernel_r_grad, recurrent_kernel_h_grad], axis=-1)

        return in_grad, kernel_grad, r_kernel_grad


class softmax_cross_entropy(operator):
    def __init__(self):
        super(softmax_cross_entropy, self).__init__()

    def forward(self, input, labels):
        """
        # Arguments
            input: numpy array with shape (batch, num_class)
            labels: numpy array with shape (batch,)
            eps: float, precision to avoid overflow

        # Returns
            output: scalar, average loss
            probs: the probability of each category
        """
        # precision to avoid overflow
        eps = 1e-12

        batch = len(labels)
        input_shift = input - np.max(input, axis=1, keepdims=True)
        Z = np.sum(np.exp(input_shift), axis=1, keepdims=True)

        log_probs = input_shift - np.log(Z+eps)
        probs = np.exp(log_probs)
        output = -1 * np.sum(log_probs[np.arange(batch), labels]) / batch
        return output, probs

    def backward(self, input, labels):
        """
        # Arguments
            input: numpy array with shape (batch, num_class)
            labels: numpy array with shape (batch,)
            eps: float, precision to avoid overflow

        # Returns
            in_grad: gradient to forward input of softmax cross entropy, with shape (batch, num_class)
        """
        # precision to avoid overflow
        eps = 1e-12

        batch = len(labels)
        input_shift = input - np.max(input, axis=1, keepdims=True)
        Z = np.sum(np.exp(input_shift), axis=1, keepdims=True)
        log_probs = input_shift - np.log(Z+eps)
        probs = np.exp(log_probs)

        in_grad = probs.copy()
        in_grad[np.arange(batch), labels] -= 1
        in_grad /= batch
        return in_grad

        