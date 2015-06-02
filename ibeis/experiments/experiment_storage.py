from __future__ import absolute_import, division, print_function
import six
import numpy as np
#import six
import utool
import utool as ut
print, print_, printDBG, rrr, profile = utool.inject(
    __name__, '[expt_harn]')


@six.add_metaclass(ut.ReloadingMetaclass)
class TestResult(object):
    def __init__(test_result, cfg_list, cfgx2_lbl, lbl, testnameid, cfgx2_cfgresinfo, cfgx2_qreq_, daids, qaids):
        test_result.qaids = qaids
        test_result.daids = daids
        test_result.cfg_list         = cfg_list
        test_result.cfgx2_lbl        = cfgx2_lbl
        test_result.lbl              = lbl
        test_result.testnameid       = testnameid
        test_result.cfgx2_cfgresinfo = cfgx2_cfgresinfo
        test_result.cfgx2_qreq_      = cfgx2_qreq_

    @ut.memoize
    def get_rank_mat(test_result):
        # Ranks of Best Results
        cfgx2_bestranks = ut.get_list_column(test_result.cfgx2_cfgresinfo, 'qx2_bestranks')
        rank_mat = np.vstack(cfgx2_bestranks).T  # concatenate each query rank across configs
        # Set invalid ranks to the worse possible rank
        worst_possible_rank = test_result.get_worst_possible_rank()
        rank_mat[rank_mat == -1] =  worst_possible_rank
        return rank_mat

    def get_worst_possible_rank(test_result):
        #worst_possible_rank = max(9001, len(test_result.daids) + 1)
        worst_possible_rank = len(test_result.daids) + 1
        return worst_possible_rank

    @ut.memoize
    def get_new_hard_qx_list(test_result):
        """ Mark any query as hard if it didnt get everything correct """
        rank_mat = test_result.get_rank_mat()
        is_new_hard_list = rank_mat.max(axis=1) > 0
        new_hard_qx_list = np.where(is_new_hard_list)[0]
        return new_hard_qx_list

    def get_rank_histograms(test_result):
        rank_mat = test_result.get_rank_mat()
        bins = test_result.get_rank_histogram_bins()
        config_hists = []
        for ranks in rank_mat.T:
            bin_values, bin_edges  = np.histogram(ranks, bins=bins)
            bin_keys = list(zip(bin_edges[:-1], bin_edges[1:]))
            hist_dict = dict(zip(bin_keys, bin_values))
            config_hists.append(hist_dict)
        return config_hists

    def get_rank_histogram_bins(test_result):
        worst_possible_rank = test_result.get_worst_possible_rank()
        if worst_possible_rank > 50:
            bins = [0, 1, 5, 50, worst_possible_rank, worst_possible_rank + 1]
        elif worst_possible_rank > 5:
            bins = [0, 1, 5, worst_possible_rank, worst_possible_rank + 1]
        else:
            bins = [0, 1, 5]
        return bins

    def get_rank_histogram_bin_edges(test_result):
        bins = test_result.get_rank_histogram_bins()
        bin_keys = list(zip(bins[:-1], bins[1:]))
        return bin_keys

    def get_rank_histogram_qx_binxs(test_result):
        rank_mat = test_result.get_rank_mat()
        config_hists = test_result.get_rank_histograms()
        config_binxs = []
        bin_keys = test_result.get_rank_histogram_bin_edges()
        for hist_dict, ranks in zip(config_hists, rank_mat.T):
            bin_qxs = [np.where(np.logical_and(low <= ranks, ranks < high))[0]
                       for low, high in bin_keys]
            qx2_binx = -np.ones(len(ranks))
            for binx, qxs in enumerate(bin_qxs):
                qx2_binx[qxs] = binx
            config_binxs.append(qx2_binx)
        return config_binxs

    def get_rank_histogram_qx_sample(test_result, size=10):
        size = 10
        rank_mat = test_result.get_rank_mat()
        config_hists = test_result.get_rank_histograms()
        config_rand_bin_qxs = []
        bins = test_result.get_rank_histogram_bins()
        bin_keys = list(zip(bins[:-1], bins[1:]))
        randstate = np.random.RandomState(seed=0)
        for hist_dict, ranks in zip(config_hists, rank_mat.T):
            bin_qxs = [np.where(np.logical_and(low <= ranks, ranks < high))[0]
                       for low, high in bin_keys]
            rand_bin_qxs = [qxs if len(qxs) <= size else
                            randstate.choice(qxs, size=size, replace=False)
                            for qxs in bin_qxs]
            config_rand_bin_qxs.append(rand_bin_qxs)
        return config_rand_bin_qxs

    def get_full_cfgstr(test_result, cfgx):
        """ both qaids and daids included """
        full_cfgstr = test_result.cfgx2_qreq_[cfgx].get_full_cfgstr()
        return full_cfgstr

    def get_cfgstr(test_result, cfgx):
        """ just daids and config_str """
        cfgstr = test_result.cfgx2_qreq_[cfgx].get_cfgstr()
        return cfgstr


@six.add_metaclass(ut.ReloadingMetaclass)
class ResultMetadata(object):
    def __init__(metadata, fpath, autoconnect=False):
        """
        metadata_fpath = join(figdir, 'result_metadata.shelf')
        metadata = ResultMetadata(metadata_fpath)
        """
        metadata.fpath = fpath
        metadata.dimensions = ['query_cfgstr', 'qaid']
        metadata._shelf = None
        metadata.dictstore = None
        if autoconnect:
            metadata.connect()

    def connect(metadata):
        import shelve
        metadata._shelf = shelve.open(metadata.fpath)
        if 'dictstore' not in metadata._shelf:
            dictstore = ut.AutoVivification()
            metadata._shelf['dictstore'] = dictstore
        metadata.dictstore = metadata._shelf['dictstore']

    def clear(metadata):
        dictstore = ut.AutoVivification()
        metadata._shelf['dictstore'] = dictstore
        metadata.dictstore = metadata._shelf['dictstore']

    def __del__(metadata):
        metadata.close()

    def close(metadata):
        metadata._shelf.close()

    def write(metadata):
        metadata._shelf['dictstore'] = metadata.dictstore
        metadata._shelf.sync()

    def set_global_data(metadata, cfgstr, qaid, key, val):
        metadata.dictstore[cfgstr][qaid][key] = val

    def sync_test_results(metadata, test_result):
        """ store all test results in the shelf """
        for cfgx in range(len(test_result.cfgx2_qreq_)):
            cfgstr = test_result.get_cfgstr(cfgx)
            qaids = test_result.qaids
            cfgresinfo = test_result.cfgx2_cfgresinfo[cfgx]
            for key, val_list in six.iteritems(cfgresinfo):
                for qaid, val in zip(qaids, val_list):
                    metadata.set_global_data(cfgstr, qaid, key, val)
        metadata.write()

    def get_cfgstr_list(metadata):
        cfgstr_list = list(metadata.dictstore.keys())
        return cfgstr_list

    def get_column_keys(metadata):
        unflat_colname_list = [
            [cols.keys() for cols in qaid2_cols.values()]
            for qaid2_cols in six.itervalues(metadata.dictstore)
        ]
        colname_list = ut.unique_keep_order2(ut.flatten(ut.flatten(unflat_colname_list)))
        return colname_list

    def get_square_data(metadata, cfgstr=None):
        # can only support one config at a time right now
        if cfgstr is None:
            cfgstr = metadata.get_cfgstr_list()[0]
        qaid2_cols = metadata.dictstore[cfgstr]
        qaids = list(qaid2_cols.keys())
        col_name_list = ut.unique_keep_order2(ut.flatten([cols.keys() for cols in qaid2_cols.values()]))
        #col_name_list = ['qx2_scoreexpdiff', 'qx2_gt_aid']
        #colname2_colvals = [None for colname in col_name_list]
        column_list = [
            [colvals.get(colname, None) for qaid, colvals in six.iteritems(qaid2_cols)]
            for colname in col_name_list]
        col_name_list = ['qaids'] + col_name_list
        column_list = [qaids] + column_list
        print('depth_profile(column_list) = %r' % (ut.depth_profile(column_list),))
        return col_name_list, column_list