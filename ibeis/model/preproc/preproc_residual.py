"""
"""
from __future__ import absolute_import, division, print_function
import utool as ut
(print, print_, printDBG, rrr, profile) = ut.inject(__name__, '[preproc_residual]')


def add_residual_params_gen(ibs, fid_list, qreq_=None):
    return None


def on_delete(ibs, featweight_rowid_list):
    print('Warning: Not Implemented')
    print('Probably nothing to do here')


if __name__ == '__main__':
    testable_list = [
    ]
    ut.doctest_funcs(testable_list)