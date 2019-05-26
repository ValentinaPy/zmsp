#

# simple feed forward layers

import numpy as np
from collections import Iterable
import math

from ..backends import BK
from .basic import BasicNode, ActivationHelper, Dropout, FreezeRop
from msp.utils import zcheck, zwarn, zlog, Random

# ===== Linear/Affine Nodes
# linear layer with selectable activation functions
# [inputs] or input -> output
class Affine(BasicNode):
    # n_ins: [n_ins0, n_ins1, ...]
    def __init__(self, pc, n_ins, n_out, act="linear", bias=True, affine2=True, name=None, init_rop=None):
        super().__init__(pc, name, init_rop)
        # list of n_ins and n_outs have different meanings: horizontal and vertical
        if not isinstance(n_ins, Iterable):
            n_ins = [n_ins]
        # dimensions
        self.n_ins = n_ins
        self.n_out = n_out
        # activations
        self.act = act
        self._act_f = ActivationHelper.get_act(act)
        # params
        self.bias = bias
        self.ws = []
        for i, din in enumerate(n_ins):
            self.ws.append(self.add_param(name="W", shape=(n_out, din)))
        if bias:
            self.b = self.add_param(name="B", shape=(n_out, ))
        #
        self.direct_matmul = (len(n_ins)==1 and not bias)
        # =====
        # refreshed values
        self.drop_node = self.add_sub_node("drop", Dropout(pc, (self.n_out,)))
        self._input_list = self._init_input_list()
        #
        self._affine_f = BK.affine2 if affine2 else BK.affine

    def _init_input_list(self):
        # called when refresh
        if self.bias:
            input_lists = [self.b]
        else:
            input_lists = [BK.zeros((self.n_out,))]
        for i in range(len(self.n_ins)):
            input_lists.extend([self.ws[i], None])
        return input_lists

    # fill in the list
    def _fill_input_list(self, inputs):
        for i, one in enumerate(inputs):
            self._input_list[2+2*i] = one
        return self._input_list

    def __repr__(self):
        return "# Affine: %s (%s -> %s [%s])" % (self.name, self.n_ins, self.n_out, self.act)

    def __call__(self, input_exp):
        if self.direct_matmul:
            h0 = BK.matmul(input_exp, BK.transpose(self.ws[0], 0, 1))
        else:
            if not isinstance(input_exp, (list, tuple)):
                input_exp = [input_exp]
            zcheck(len(input_exp) == len(self.n_ins), "Unmatched input sizes!")
            input_lists = self._fill_input_list(input_exp)
            h0 = self._affine_f(input_lists)
        h1 = self._act_f(h0)
        h2 = self.drop_node(h1)
        return h2

    def get_output_dims(self, *input_dims):
        return (self.n_out, )

# ==========
# special ones
class LayerNorm(BasicNode):
    def __init__(self, pc, size, a_init=1., eps=1e-6, name=None):
        super().__init__(pc, name, None)
        # todo(+N): is this all right?
        a_init_v = np.sqrt(3./size) if a_init is None else a_init
        self.size = size
        self.a_2 = self.add_param(name="A", shape=(size, ), init=np.full(size, a_init_v, dtype=np.float32))
        self.b_2 = self.add_param(name="B", shape=(size, ), init=np.zeros(size, dtype=np.float32))
        self.eps = eps
        # no droput here

    def __call__(self, x):
        mean = x.mean(-1, keepdim=True)
        std = x.std(-1, keepdim=True)
        return self.a_2 * (x - mean) / (std + self.eps) + self.b_2

# ===== Looking up Nodes
# like an embedding, usually used as the score matrix
class MatrixNode(BasicNode):
    def __init__(self, pc, n_entries, n_dim, npvec=None, name=None, init_rop=None):
        super().__init__(pc, name, init_rop)
        #
        if npvec is not None:
            self.W = self.add_param("W", (n_entries, n_dim), init=npvec)
        else:
            assert self.rop.trainable, "No meaning for the setting of un-trainable un-init Node."
            self.W = self.add_param("W", (n_entries, n_dim), init="zeros")
        self.n_dim = n_dim

    def get_output_dims(self, *input_dims):
        return (self.n_dim, )

    # no dropouts
    def __call__(self, input_idxes):
        # similar to Embedding
        if isinstance(input_idxes, int):
            input_idxes = [input_idxes]
        return BK.select(self.W, input_idxes, 0)

# embedding layer
# [inputs] or input -> (batched) output
class Embedding(BasicNode):
    def __init__(self, pc, n_words, n_dim, fix_row0=True, dropout_wordceil=None, npvec=None, name=None, init_rop=None, freeze=False):
        super(Embedding, self).__init__(pc, name, init_rop)
        if npvec is not None:
            zcheck(len(npvec.shape) == 2 and npvec.shape[0] == n_words and npvec.shape[1] == n_dim, "Wrong dimension for init embeddings.")
            zlog("Add embed W from npvec %s." % (npvec.shape,))
            if freeze:
                self.rop.add_fixed_value("trainable", False)
        else:
            if freeze:
                self.rop.add_fixed_value("trainable", False)
                zwarn("Meaningless to freeze random embeddings?")
        self.E = self.add_param("E", (n_words, n_dim), init=npvec, lookup=True)
        #
        self.n_words = n_words
        self.n_dim = n_dim
        self.fix_row0 = fix_row0
        self.dropout_wordceil_hp = dropout_wordceil
        self.dropout_wordceil = dropout_wordceil if dropout_wordceil is not None else n_words
        # refreshed values
        self._input_f = None
        self.drop_node = self.add_sub_node("drop", Dropout(pc, (self.n_dim,)))

    # special one
    def replace_weights(self, npvec):
        num_words, num_dim = npvec.shape
        zcheck(num_dim == self.n_dim, "Cannot change embedding dimension!")
        # replace
        # todo(+N): simply add one param here, the original one is still around
        zlog(f"Replacing the embedding weights from ({self.n_words}, {num_dim}) to ({num_words}, {num_dim})")
        self.E = self.add_param("E", (num_words, num_dim), init=npvec, lookup=True)
        self.n_words = num_words
        self.dropout_wordceil = self.dropout_wordceil_hp if self.dropout_wordceil_hp is not None else self.n_words

    def _input_f_obtain(self, edrop):
        if edrop <= 0.:
            return lambda x: x
        else:
            # todo(warn): replaced sample, maybe an efficient but approx. impl & only works for 2d
            edrop_rands = Random.random_sample((int(self.dropout_wordceil*edrop),), "sample")    # [0,1)
            edrop_idxes = [int(self.dropout_wordceil*z) for z in edrop_rands]
            edrop_set = set(edrop_idxes)
            return lambda x: [0 if one in edrop_set else one for one in x]      # drop to 0 if fall in the set

    def refresh(self, rop=None):
        super().refresh(rop)
        if self.fix_row0:
            # todo(warn): zero for idx 0
            BK.zero_row(self.E, 0)
        #
        self._input_f = self._input_f_obtain(self.rop.edrop)

    def __repr__(self):
        return "# Embedding (dim=%s, num=%s)" % (self.n_dim, self.n_words)

    def __call__(self, input_idxes):
        # input should be a list of ints or int
        if isinstance(input_idxes, int):
            input_idxes = [input_idxes]
        input_lists = self._input_f(input_idxes)
        h0 = BK.lookup(self.E, input_lists)
        h1 = self.drop_node(h0)
        return h1

    def get_output_dims(self, *input_dims):
        return (self.n_dim, )

# sin/cos fixed positional embedding
# mainly from OpenNMT
class PosiEmbedding(BasicNode):
    def __init__(self, pc: BK.ParamCollection, n_dim: int, max_len: int=5000, init_sincos: bool=True,
                 freeze: bool=True, no_dropout: bool=True):
        super().__init__(pc, None, None)
        # init from sin/cos values
        self.init_sincos = init_sincos
        if init_sincos:
            pe = np.zeros([max_len, n_dim])
            position = np.arange(0, max_len).reshape([-1, 1])
            div_term = np.exp((np.arange(0, n_dim, 2) * -(math.log(10000.0)/n_dim)))
            div_results = position * div_term
            pe[:, 0::2] = np.sin(div_results)
            pe[:, 1::2] = np.cos(div_results)
            # make it similar to the range of plain Embedding
            pe *= np.sqrt(3./n_dim)
            if freeze:
                self.rop.add_fixed_value("trainable", False)
            else:
                zwarn("Init-from sin/cos positional embeddings should be freezed?")
        else:
            pe = None
            if freeze:
                self.rop.add_fixed_value("trainable", False)
                zwarn("Meaningless to freeze random embeddings?")
        #
        self.dim = n_dim
        self.max_len = max_len
        self.E = self.add_param("E", (max_len, n_dim), init=pe, lookup=True)
        if no_dropout:
            self.drop_node = lambda x:x
        else:
            self.drop_node = self.add_sub_node("drop", Dropout(pc, (self.dim,)))

    def get_output_dims(self, *input_dims):
        return (self.dim, )

    def __repr__(self):
        return "# PositionalEmbedding (dim=%s, max=%s), init-sin/cos=%s" % (self.dim, self.max_len, self.init_sincos)

    def __call__(self, input_idxes):
        # input should be a list of ints or int
        if isinstance(input_idxes, int):
            input_idxes = [input_idxes]
        clamped_idx_repr = BK.clamp(BK.input_idx(input_idxes), max=self.max_len)
        h0 = BK.lookup(self.E, clamped_idx_repr)
        h1 = self.drop_node(h0)
        return h1
