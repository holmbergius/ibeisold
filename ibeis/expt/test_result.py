# -*- coding: utf-8 -*-
"""
TODO:
    save and load TestResult classes
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import six
import numpy as np
#import six
from six.moves import zip, range, map  # NOQA
import vtool as vt
import utool as ut
from ibeis.expt import cfghelpers
from ibeis.expt import experiment_helpers  # NOQA
print, print_, printDBG, rrr, profile = ut.inject(
    __name__, '[expt_harn]')

from ibeis.expt.old_storage import ResultMetadata  # NOQA


def combine_testres_list(ibs, testres_list):
    """
    combine test results over multiple annot configs

    CommandLine:
        python -m ibeis --tf combine_testres_list

        python -m ibeis.expt.experiment_drawing --exec-draw_rank_cdf --db PZ_MTEST --show
        python -m ibeis.expt.experiment_drawing --exec-draw_rank_cdf --db PZ_Master0 --show
        python -m ibeis.expt.experiment_drawing --exec-draw_rank_cdf --db PZ_MTEST --show -a varysize -t default
        python -m ibeis.expt.experiment_drawing --exec-draw_rank_cdf --db PZ_MTEST --show -a varysize -t default

    >>> # DISABLE_DOCTEST
    >>> from ibeis.expt.test_result import *  # NOQA
    >>> from ibeis.expt import experiment_harness
    >>> ibs, testres_list = experiment_harness.testdata_expts('PZ_MTEST', ['varysize'])
    >>> combine_testres_list(ibs, testres_list)
    """
    #try:
    #    assert ut.list_allsame([testres.qaids for testres in testres_list]), ' cannot handle non-same qaids right now'
    #except AssertionError as ex:
    #    ut.printex(ex)
    #    raise
    import copy
    from ibeis.expt import annotation_configs

    acfg_list = [testres.acfg for testres in testres_list]
    acfg_lbl_list = annotation_configs.get_varied_acfg_labels(acfg_list)

    flat_acfg_list = annotation_configs.flatten_acfg_list(acfg_list)
    nonvaried_acfg, varied_acfg_list = cfghelpers.partition_varied_cfg_list(flat_acfg_list)

    def combine_lbls(lbl, acfg_lbl):
        if len(lbl) == 0:
            return acfg_lbl
        if len(acfg_lbl) == 0:
            return lbl
        return lbl + '+' + acfg_lbl

    #qaids = testres.qaids
    agg_cfg_list        = ut.flatten(
        [testres.cfg_list for testres in testres_list])
    agg_cfgx2_cfgreinfo = ut.flatten(
        [testres.cfgx2_cfgresinfo for testres in testres_list])
    agg_cfgx2_qreq_     = ut.flatten(
        [testres.cfgx2_qreq_ for testres in testres_list])
    agg_cfgdict_list    = ut.flatten(
        [testres.cfgdict_list for testres in testres_list])
    agg_varied_acfg_list = ut.flatten([
        [acfg] * len(testres.cfg_list)
        for testres, acfg in zip(testres_list, varied_acfg_list)
    ])
    agg_cfgx2_lbls      = ut.flatten(
        [[combine_lbls(lbl, acfg_lbl) for lbl in testres.cfgx2_lbl]
         for testres, acfg_lbl in zip(testres_list, acfg_lbl_list)])

    agg_cfgx2_acfg = ut.flatten(
        [[copy.deepcopy(acfg)] * len(testres.cfg_list) for
         testres, acfg in zip(testres_list, acfg_list)])

    big_testres = TestResult(agg_cfg_list, agg_cfgx2_lbls,
                             agg_cfgx2_cfgreinfo, agg_cfgx2_qreq_)

    # Give the big test result an acfg that is common between everything
    big_testres.acfg = annotation_configs.unflatten_acfgdict(nonvaried_acfg)
    big_testres.cfgdict_list = agg_cfgdict_list  # TODO: depricate

    big_testres.common_acfg = annotation_configs.compress_aidcfg(big_testres.acfg)
    big_testres.common_cfgdict = reduce(ut.dict_intersection, big_testres.cfgdict_list)
    big_testres.varied_acfg_list = agg_varied_acfg_list
    big_testres.varied_cfg_list = [
        ut.delete_dict_keys(cfgdict.copy(), list(big_testres.common_cfgdict.keys()))
        for cfgdict in big_testres.cfgdict_list]
    big_testres.acfg_list = acfg_list
    big_testres.cfgx2_acfg = agg_cfgx2_acfg
    big_testres.cfgx2_pcfg = agg_cfgdict_list

    assert len(agg_cfgdict_list) == len(agg_cfgx2_acfg)

    #big_testres.acfg
    testres = big_testres
    # big_testres = testres
    return testres


@six.add_metaclass(ut.ReloadingMetaclass)
class TestResult(object):
    def __init__(testres, cfg_list, cfgx2_lbl, cfgx2_cfgresinfo, cfgx2_qreq_):
        assert len(cfg_list) == len(cfgx2_lbl), (
            'bad lengths1: %r != %r' % (len(cfg_list), len(cfgx2_lbl)))
        assert len(cfgx2_qreq_) == len(cfgx2_lbl), (
            'bad lengths2: %r != %r' % (len(cfgx2_qreq_), len(cfgx2_lbl)))
        assert len(cfgx2_cfgresinfo) == len(cfgx2_lbl), (
            'bad lengths3: %r != %r' % (len(cfgx2_cfgresinfo), len(cfgx2_lbl)))
        #testres._qaids = qaids
        #testres.daids = daids
        testres.cfg_list         = cfg_list
        testres.cfgx2_lbl        = cfgx2_lbl
        testres.cfgx2_cfgresinfo = cfgx2_cfgresinfo
        testres.cfgx2_qreq_      = cfgx2_qreq_
        testres.lbl              = None
        testres.testnameid       = None

    @property
    def ibs(testres):
        ibs_list = [qreq_.ibs for qreq_ in testres.cfgx2_qreq_]
        ibs = ibs_list[0]
        for ibs_ in ibs_list:
            assert ibs is ibs_, 'not all query requests are using the same controller'
        return ibs

    @property
    def qaids(testres):
        assert testres.has_constant_qaids(), 'must have constant qaids to use this property'
        return testres.cfgx2_qaids[0]
        #return testres._qaids

    @property
    def nConfig(testres):
        return len(testres.cfg_list)

    @property
    def nQuery(testres):
        return len(testres.qaids)

    @property
    def rank_mat(testres):
        return testres.get_rank_mat()

    @property
    def cfgx2_daids(testres):
        daids_list = [qreq_.get_external_daids() for qreq_ in testres.cfgx2_qreq_]
        return daids_list

    @property
    def cfgx2_qaids(testres):
        qaids_list = [qreq_.get_external_qaids() for qreq_ in testres.cfgx2_qreq_]
        return qaids_list

    def has_constant_daids(testres):
        return ut.list_allsame(testres.cfgx2_daids)

    def has_constant_qaids(testres):
        return ut.list_allsame(testres.cfgx2_qaids)

    def has_constant_length_daids(testres):
        return ut.list_allsame(list(map(len, testres.cfgx2_daids)))

    def has_constant_length_qaids(testres):
        return ut.list_allsame(list(map(len, testres.cfgx2_qaids)))

    def get_infoprop_list(testres, key, qaids=None):
        _tmp1_cfgx2_infoprop = ut.get_list_column(testres.cfgx2_cfgresinfo, key)
        _tmp2_cfgx2_infoprop = list(map(
            np.array,
            ut.util_list.replace_nones(_tmp1_cfgx2_infoprop, np.nan)))
        if qaids is not None:
            flags_list = [np.in1d(aids_, qaids) for aids_ in testres.cfgx2_qaids]
            cfgx2_infoprop = vt.zipcompress(_tmp2_cfgx2_infoprop, flags_list)
        else:
            cfgx2_infoprop = _tmp2_cfgx2_infoprop
        if key == 'qx2_bestranks' or key.endswith('_rank'):
            # hack
            for infoprop in cfgx2_infoprop:
                infoprop[infoprop == -1] = testres.get_worst_possible_rank()
        return cfgx2_infoprop

    def get_infoprop_mat(testres, key, qaids=None):
        """
        key = 'qx2_gf_raw_score'
        key = 'qx2_gt_raw_score'
        """
        cfgx2_infoprop = testres.get_infoprop_list(key, qaids)
        # concatenate each query rank across configs
        infoprop_mat = np.vstack(cfgx2_infoprop).T
        return infoprop_mat

    @ut.memoize
    def get_rank_mat(testres, qaids=None):
        # Ranks of Best Results
        #get_infoprop_mat(testres, 'qx2_bestranks')
        rank_mat = testres.get_infoprop_mat(key='qx2_bestranks', qaids=qaids)
        #cfgx2_bestranks = ut.get_list_column(testres.cfgx2_cfgresinfo, 'qx2_bestranks')
        #rank_mat = np.vstack(cfgx2_bestranks).T  # concatenate each query rank across configs
        # Set invalid ranks to the worse possible rank
        #worst_possible_rank = testres.get_worst_possible_rank()
        #rank_mat[rank_mat == -1] =  worst_possible_rank
        return rank_mat

    def get_worst_possible_rank(testres):
        #worst_possible_rank = max(9001, len(testres.daids) + 1)
        worst_possible_rank = max([len(qreq_.get_external_daids()) for qreq_ in testres.cfgx2_qreq_]) + 1
        #worst_possible_rank = len(testres.daids) + 1
        return worst_possible_rank

    def get_rank_histograms(testres, bins=None, asdict=True, jagged=False):
        if bins is None:
            bins = testres.get_rank_histogram_bins()
        elif bins == 'dense':
            bins = np.arange(testres.get_worst_possible_rank() + 1)
        if jagged:
            assert not asdict
            cfgx2_bestranks = testres.get_infoprop_list('qx2_bestranks')
            cfgx2_bestranks = [
                ut.list_replace(bestranks, -1, testres.get_worst_possible_rank())
                for bestranks in cfgx2_bestranks]
            cfgx2_hist = np.zeros((len(cfgx2_bestranks), len(bins) - 1), dtype=np.int32)
            for cfgx, ranks in enumerate(cfgx2_bestranks):
                bin_values, bin_edges  = np.histogram(ranks, bins=bins)
                assert len(ranks) == bin_values.sum(), 'should sum to be equal'
                cfgx2_hist[cfgx] = bin_values
            return cfgx2_hist, bin_edges

        rank_mat = testres.get_rank_mat()
        if not asdict:
            # Use numpy histogram repr
            config_hists = np.zeros((len(rank_mat.T), len(bins) - 1), dtype=np.int32)
        else:
            config_hists = []
            pass
        bin_sum = None
        for cfgx, ranks in enumerate(rank_mat.T):
            bin_values, bin_edges  = np.histogram(ranks, bins=bins)
            if bin_sum is None:
                bin_sum = bin_values.sum()
            else:
                assert bin_sum == bin_values.sum(), 'should sum to be equal'
            if asdict:
                # Use dictionary histogram repr
                bin_keys = list(zip(bin_edges[:-1], bin_edges[1:]))
                hist_dict = dict(zip(bin_keys, bin_values))
                config_hists.append(hist_dict)
            else:
                config_hists[cfgx] = bin_values
        if not asdict:
            return config_hists, bin_edges
        else:
            return config_hists

    def get_rank_cumhist(testres, bins='dense'):
        #testres.rrr()
        hist_list, edges = testres.get_rank_histograms(bins, asdict=False)
        config_cdfs = np.cumsum(hist_list, axis=1)
        return config_cdfs, edges

    def get_rank_percentage_cumhist(testres, bins='dense'):
        r"""
        Args:
            bins (unicode): (default = u'dense')

        Returns:
            tuple: (config_cdfs, edges)

        CommandLine:
            python -m ibeis --tf TestResult.get_rank_percentage_cumhist
            python -m ibeis --tf TestResult.get_rank_percentage_cumhist -t baseline -a uncontrolled ctrl

        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.experiment_drawing import *  # NOQA
            >>> from ibeis.init import main_helpers
            >>> ibs, testres = main_helpers.testdata_expts('PZ_MTEST')
            >>> bins = u'dense'
            >>> (config_cdfs, edges) = testres.get_rank_percentage_cumhist(bins)
            >>> result = ('(config_cdfs, edges) = %s' % (str((config_cdfs, edges)),))
            >>> print(result)
        """
        #testres.rrr()
        cfgx2_hist, edges = testres.get_rank_histograms(bins, asdict=False, jagged=True)
        cfgx2_cumhist = np.cumsum(cfgx2_hist, axis=1)
        cfgx2_cumhist_percent = 100 * cfgx2_cumhist / cfgx2_cumhist.T[-1].T[:, None]
        return cfgx2_cumhist_percent, edges

    def get_rank_histogram_bins(testres):
        """ easy to see histogram bins """
        worst_possible_rank = testres.get_worst_possible_rank()
        if worst_possible_rank > 50:
            bins = [0, 1, 5, 50, worst_possible_rank, worst_possible_rank + 1]
        elif worst_possible_rank > 5:
            bins = [0, 1, 5, worst_possible_rank, worst_possible_rank + 1]
        else:
            bins = [0, 1, 5]
        return bins

    def get_rank_histogram_bin_edges(testres):
        bins = testres.get_rank_histogram_bins()
        bin_keys = list(zip(bins[:-1], bins[1:]))
        return bin_keys

    def get_rank_histogram_qx_binxs(testres):
        rank_mat = testres.get_rank_mat()
        config_hists = testres.get_rank_histograms()
        config_binxs = []
        bin_keys = testres.get_rank_histogram_bin_edges()
        for hist_dict, ranks in zip(config_hists, rank_mat.T):
            bin_qxs = [np.where(np.logical_and(low <= ranks, ranks < high))[0]
                       for low, high in bin_keys]
            qx2_binx = -np.ones(len(ranks))
            for binx, qxs in enumerate(bin_qxs):
                qx2_binx[qxs] = binx
            config_binxs.append(qx2_binx)
        return config_binxs

    def get_rank_histogram_qx_sample(testres, size=10):
        size = 10
        rank_mat = testres.get_rank_mat()
        config_hists = testres.get_rank_histograms()
        config_rand_bin_qxs = []
        bins = testres.get_rank_histogram_bins()
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

    def get_X_LIST(testres):
        #X_LIST = ut.get_argval('--rank-lt-list', type_=list, default=[1])
        X_LIST = ut.get_argval('--rank-lt-list', type_=list, default=[1, 5])
        return X_LIST

    def get_nLessX_dict(testres):
        # Build a (histogram) dictionary mapping X (as in #ranks < X) to a list of cfg scores
        X_LIST = testres.get_X_LIST()
        nLessX_dict = {int(X): np.zeros(testres.nConfig) for X in X_LIST}
        cfgx2_qx2_bestrank = testres.get_infoprop_list('qx2_bestranks')
        #rank_mat = testres.rank_mat  # HACK
        for X in X_LIST:
            cfgx2_lessX_mask = [
                np.logical_and(0 <= qx2_ranks, qx2_ranks < X)
                for qx2_ranks in cfgx2_qx2_bestrank]
            #lessX_ = np.logical_and(np.less(rank_mat, X), np.greater_equal(rank_mat, 0))
            cfgx2_nLessX = np.array([lessX_.sum(axis=0) for lessX_ in cfgx2_lessX_mask])
            nLessX_dict[int(X)] = cfgx2_nLessX
        return nLessX_dict

    def get_all_varied_params(testres):
        # only for big results
        varied_cfg_params = list(set(ut.flatten(
            [cfgdict.keys()
             for cfgdict in testres.varied_cfg_list])))
        varied_acfg_params = list(set(ut.flatten([
            acfg.keys()
            for acfg in testres.varied_acfg_list])))
        varied_params = varied_acfg_params + varied_cfg_params
        return varied_params

    def get_total_num_varied_params(testres):
        return len(testres.get_all_varied_params())

    def get_param_basis(testres, key):
        """
        Returns what a param was varied between over all tests
        key = 'K'
        key = 'dcfg_sample_size'
        """
        if key == 'len(daids)':
            basis = sorted(list(set([len(daids) for daids in testres.cfgx2_daids])))
        elif any([key in cfgdict for cfgdict in testres.varied_cfg_list]):
            basis = sorted(list(set([
                cfgdict[key]
                for cfgdict in testres.varied_cfg_list])))
        elif any([key in cfgdict for cfgdict in testres.varied_acfg_list]):
            basis = sorted(list(set([
                acfg[key]
                for acfg in testres.varied_acfg_list])))
        else:
            assert False
        return basis

    def get_param_val_from_cfgx(testres, cfgx, key):
        if key == 'len(daids)':
            return len(testres.cfgx2_daids[cfgx])
        elif any([key in cfgdict for cfgdict in testres.varied_cfg_list]):
            return testres.varied_cfg_list[cfgx][key]
        elif any([key in cfgdict for cfgdict in testres.varied_acfg_list]):
            return testres.varied_acfg_list[cfgx][key]
        else:
            assert False

    def get_cfgx_with_param(testres, key, val):
        """
        Gets configs where the given parameter is held constant
        """
        if key == 'len(daids)':
            cfgx_list = [cfgx for cfgx, daids in enumerate(testres.cfgx2_daids)
                         if len(daids) == val]
        elif any([key in cfgdict for cfgdict in testres.varied_cfg_list]):
            cfgx_list = [cfgx for cfgx, cfgdict in enumerate(testres.varied_cfg_list)
                         if cfgdict[key] == val]
        elif any([key in cfgdict for cfgdict in testres.varied_acfg_list]):
            cfgx_list = [cfgx for cfgx, acfg in enumerate(testres.varied_acfg_list)
                         if acfg[key] == val]
        else:
            assert False
        return cfgx_list

    def get_full_cfgstr(testres, cfgx):
        """ both qannots and dannots included """
        full_cfgstr = testres.cfgx2_qreq_[cfgx].get_full_cfgstr()
        return full_cfgstr

    @ut.memoize
    def get_cfgstr(testres, cfgx):
        """ just dannots and config_str """
        cfgstr = testres.cfgx2_qreq_[cfgx].get_cfgstr()
        return cfgstr

    def _shorten_lbls(testres, lbl):
        import re
        repl_list = [
            ('candidacy_', ''),
            ('viewpoint_compare', 'viewpoint'),
            #('custom', 'default'),
            ('fg_on', 'FG'),
            ('sv_on', 'SV'),
            ('rotation_invariance', 'RI'),
            ('affine_invariance', 'AI'),
            ('augment_queryside_hack', 'QRH'),
            ('nNameShortlistSVER', 'nRR'),
            #
            #('sample_per_ref_name', 'per_ref_name'),
            ('sample_per_ref_name', 'per_gt_name'),
            ('require_timestamp=True', 'require_timestamp'),
            ('require_timestamp=False,?', ''),
            ('require_timestamp=None,?', ''),
            ('[_A-Za-z]*=None,?', ''),
            ('dpername=None,?', ''),
            #???
            #('sample_per_ref_name', 'per_gt_name'),
            #('per_name', 'per_gf_name'),   # Try to make labels clearer for paper
            #----
            ('prescore_method=\'?csum\'?,score_method=\'?csum\'?,?', 'csum'),
            ('prescore_method=\'?nsum\'?,score_method=\'?nsum\'?,?', 'nsum'),
            ('force_const_size=[^,]+,?', ''),
            (r'[dq]_true_size=\d+,?', ''),
            (r'_orig_size=[^,]+,?', ''),
            # Hack
            ('[qd]?exclude_reference=' + ut.regex_or(['True', 'False', 'None']) + '\,?', ''),
            #('=True', '=On'),
            #('=False', '=Off'),
            ('=True', '=T'),
            ('=False', '=F'),
        ]
        for ser, rep in repl_list:
            lbl = re.sub(ser, rep, lbl)
        return lbl

    #def _friendly_shorten_lbls(testres, lbl):
    #    import re
    #    repl_list = [
    #        ('dmingt=None,?', ''),
    #        ('qpername=None,?', ''),
    #    ]
    #    for ser, rep in repl_list:
    #        lbl = re.sub(ser, rep, lbl)
    #    return lbl

    def get_short_cfglbls(testres, friendly=False):
        """
        Labels for published tables

        cfg_lbls = ['baseline:nRR=200+default:', 'baseline:+default:']

        CommandLine:
            python -m ibeis --tf TestResult.get_short_cfglbls

        Example:
            >>> # SLOW_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> import ibeis
            >>> testres = ibeis.testdata_expts('PZ_MTEST', a=['unctrl', 'ctrl::unctrl_comp'])
            >>> cfg_lbls = testres.get_short_cfglbls(friendly=True)
            >>> result = ('cfg_lbls = %s' % (ut.list_str(cfg_lbls),))
            >>> print(result)
        """

        if False and friendly :
            acfg_names = [acfg['qcfg']['_cfgstr'] for acfg in testres.cfgx2_acfg]
            pcfg_names = [pcfg['_cfgstr'] for pcfg in testres.cfgx2_pcfg]

            # Only vary the label settings within the cfgname
            acfg_hashes = np.array(list(map(hash, acfg_names)))
            unique_hashes, a_groupxs = vt.group_indices(acfg_hashes)
            a_label_groups = []
            from ibeis.expt import annotation_configs
            for groupx in a_groupxs:
                acfg_list = ut.list_take(testres.cfgx2_acfg, groupx)
                #varied_lbls = cfghelpers.get_varied_cfg_lbls(acfg_list)
                varied_lbls = annotation_configs.get_varied_acfg_labels(
                    acfg_list, mainkey='_cfgstr')
                a_label_groups.append(varied_lbls)
            acfg_lbls = vt.invert_apply_grouping(a_label_groups, a_groupxs)

            pcfg_hashes = np.array(list(map(hash, pcfg_names)))
            unique_hashes, p_groupxs = vt.group_indices(pcfg_hashes)
            p_label_groups = []
            for groupx in p_groupxs:
                pcfg_list = ut.list_take(testres.cfgx2_pcfg, groupx)
                varied_lbls = cfghelpers.get_varied_cfg_lbls(pcfg_list, mainkey='_cfgstr')
                p_label_groups.append(varied_lbls)
            pcfg_lbls = vt.invert_apply_grouping(p_label_groups, p_groupxs)

            cfg_lbls = [albl + '+' + plbl for albl, plbl in zip(acfg_lbls, pcfg_lbls)]
        else:
            cfg_lbls = testres.cfgx2_lbl[:]
        cfg_lbls = [testres._shorten_lbls(lbl) for lbl in cfg_lbls]
        # split configs up by param and annots
        pa_tups = [lbl.split('+') for lbl in cfg_lbls]
        cfg_lbls2 = []
        for pa in pa_tups:
            new_parts = []
            for part in pa:
                _tup = part.split(cfghelpers.NAMEVARSEP)
                if len(_tup) > 1:
                    name, settings = _tup
                else:
                    name = _tup[0]
                    settings = ''
                if len(settings) == 0:
                    new_parts.append(name)
                else:
                    new_parts.append(part)
            if len(new_parts) == 2 and new_parts[1] == 'default':
                newlbl = new_parts[0]
            else:
                newlbl = '+'.join(new_parts)
            cfg_lbls2.append(newlbl)
        #cfgtups = [lbl.split(cfghelpers.NAMEVARSEP) for lbl in cfg_lbls]
        #cfg_lbls = [cfghelpers.NAMEVARSEP.join(tup) if len(tup) != 2 else tup[1] if len(tup[1]) > 0 else 'BASELINE' for tup in cfgtups]
        cfg_lbls = cfg_lbls2

        #from ibeis.expt import annotation_configs
        #lblaug = annotation_configs.compress_aidcfg(testres.acfg)['common']['_cfgstr']

        #cfg_lbls = [lbl + cfghelpers.NAMEVARSEP + lblaug for lbl in cfg_lbls]

        return cfg_lbls

    def make_figtitle(testres, plotname='', filt_cfg=None):
        """
        Helper for consistent figure titles

        CommandLine:
            python -m ibeis --tf TestResult.make_figtitle  --prefix "Seperability " --db GIRM_Master1   -a timectrl -t Ell:K=2     --hargv=scores
            python -m ibeis --tf TestResult.make_figtitle

        Example:
            >>> # ENABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> import ibeis
            >>> testres = ibeis.testdata_expts('PZ_MTEST')
            >>> plotname = ''
            >>> figtitle = testres.make_figtitle(plotname)
            >>> result = ('figtitle = %r' % (figtitle,))
            >>> print(result)
        """
        figtitle_prefix = ut.get_argval('--prefix', type_=str, default='')
        if figtitle_prefix != '':
            figtitle_prefix = figtitle_prefix.rstrip() + ' '
        figtitle = (figtitle_prefix + plotname)
        hasprefix = figtitle_prefix == ''
        if hasprefix:
            figtitle += '\n'

        title_aug = testres.get_title_aug(friendly=True, with_cfg=hasprefix)
        figtitle += ' ' + title_aug

        if filt_cfg is not None:
            filt_cfgstr = cfghelpers.get_cfg_lbl(filt_cfg)
            if filt_cfgstr.strip() != ':':
                figtitle += ' ' + filt_cfgstr
        return figtitle

    def get_title_aug(testres, with_size=True, with_db=True, with_cfg=True,
                      friendly=False):
        r"""
        Args:
            with_size (bool): (default = True)

        Returns:
            str: title_aug

        CommandLine:
            python -m ibeis --tf TestResult.get_title_aug --db PZ_Master1 -a timequalctrl::timectrl

        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> import ibeis
            >>> testres = ibeis.testdata_expts('PZ_MTEST')
            >>> with_size = True
            >>> title_aug = testres.get_title_aug(with_size)
            >>> res = u'title_aug = %s' % (title_aug,)
            >>> print(res)
        """
        ibs = testres.ibs
        title_aug = ''
        if with_db:
            title_aug += 'db=' + (ibs.get_dbname())
        if with_cfg:
            try:
                if '_cfgname' in testres.common_acfg['common']:
                    try:
                        annot_cfgname = testres.common_acfg['common']['_cfgstr']
                    except KeyError:
                        annot_cfgname = testres.common_acfg['common']['_cfgname']
                else:
                    cfgname_list = [cfg['dcfg__cfgname']
                                    for cfg in testres.varied_acfg_list]
                    cfgname_list = ut.unique_keep_order2(cfgname_list)
                    annot_cfgname = '[' + ','.join(cfgname_list) + ']'
                try:
                    pipeline_cfgname = testres.common_cfgdict['_cfgstr']
                except KeyError:
                    #pipeline_cfgname = testres.common_cfgdict['_cfgname']
                    cfgstr_list = [cfg['_cfgstr'] for cfg in testres.varied_cfg_list]
                    uniuqe_cfgstrs = ut.unique_keep_order2(cfgstr_list)
                    pipeline_cfgname = '[' + ','.join(uniuqe_cfgstrs) + ']'

                annot_cfgname = testres._shorten_lbls(annot_cfgname)
                pipeline_cfgname = testres._shorten_lbls(pipeline_cfgname)
                title_aug += ' a=' + annot_cfgname
                title_aug += ' t=' + pipeline_cfgname
            except Exception as ex:
                print(ut.dict_str(testres.common_acfg))
                print(ut.dict_str(testres.common_cfgdict))
                ut.printex(ex)
                raise
        if with_size:
            if testres.has_constant_qaids():
                title_aug += ' #qaids=%r' % (len(testres.qaids),)
            elif testres.has_constant_length_qaids():
                title_aug += ' #qaids=%r*' % (len(testres.cfgx2_qaids[0]),)
            if testres.has_constant_daids():
                daids = testres.cfgx2_daids[0]
                title_aug += ' #daids=%r' % (len(testres.cfgx2_daids[0]),)
                if testres.has_constant_qaids():
                    locals_ = ibs.get_annotconfig_stats(
                        testres.qaids, daids, verbose=False)[1]
                    all_daid_per_name_stats = locals_['all_daid_per_name_stats']
                    if all_daid_per_name_stats['std'] == 0:
                        title_aug += ' dper_name=%s' % (
                            ut.scalar_str(all_daid_per_name_stats['mean'],
                                          max_precision=2),)
                    else:
                        title_aug += ' dper_name=%s±%s' % (
                            ut.scalar_str(all_daid_per_name_stats['mean'], precision=2),
                            ut.scalar_str(all_daid_per_name_stats['std'], precision=2),)
            elif testres.has_constant_length_daids():
                daids = testres.cfgx2_daids[0]
                title_aug += ' #daids=%r*' % (len(testres.cfgx2_daids[0]),)

        if friendly:
            # Hackiness for friendliness
            #title_aug = title_aug.replace('db=PZ_Master1', 'Plains Zebras')
            #title_aug = title_aug.replace('db=NNP_MasterGIRM_core', 'Masai Giraffes')
            #title_aug = title_aug.replace('db=GZ_ALL', 'Grevy\'s Zebras')
            title_aug = ut.multi_replace(
                title_aug,
                list(ibs.const.DBNAME_ALIAS.keys()),
                list(ibs.const.DBNAME_ALIAS.values()))
            #title_aug = title_aug.replace('db=PZ_Master1', 'db=PZ')
            #title_aug = title_aug.replace('db=NNP_MasterGIRM_core', 'Masai Giraffes')
            #title_aug = title_aug.replace('db=GZ_ALL', 'Grevy\'s Zebras')
        return title_aug

    def get_fname_aug(testres, **kwargs):
        import re
        title_aug = testres.get_title_aug(**kwargs)
        valid_regex = '-a-zA-Z0-9_.() '
        valid_extra = '=,'
        valid_regex += valid_extra
        title_aug = title_aug.replace(' ', '_')  # spaces suck
        fname_aug = re.sub('[^' + valid_regex + ']+', '', title_aug)
        fname_aug = fname_aug.strip('_')
        return fname_aug

    def print_acfg_info(testres, **kwargs):
        """
        CommandLine:
            python -m ibeis --tf TestResult.print_acfg_info

        Kwargs;
            see ibs.get_annot_stats_dict
            hashid, per_name, per_qual, per_vp, per_name_vpedge, per_image,
            min_name_hourdist

        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> import ibeis
            >>> testres = ibeis.testdata_expts('PZ_MTEST', a=['ctrl::unctrl_comp'], t=['candk:K=[1,2]'])
            >>> ibs = None
            >>> result = testres.print_acfg_info()
            >>> print(result)
        """
        from ibeis.expt import annotation_configs
        ibs = testres.ibs
        # Get unique annotation configs
        cfgx2_acfg_label = annotation_configs.get_varied_acfg_labels(testres.cfgx2_acfg)
        flags = ut.flag_unique_items(cfgx2_acfg_label)
        qreq_list = ut.list_compress(testres.cfgx2_qreq_, flags)
        acfg_list = ut.list_compress(testres.cfgx2_acfg, flags)
        expanded_aids_list = [(qreq_.qaids, qreq_.daids) for qreq_ in qreq_list]
        annotation_configs.print_acfg_list(acfg_list, expanded_aids_list, ibs, **kwargs)

    def print_unique_annot_config_stats(testres, ibs=None):
        r"""
        Args:
            ibs (IBEISController):  ibeis controller object(default = None)

        CommandLine:
            python -m ibeis --tf TestResult.print_unique_annot_config_stats

        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> import ibeis
            >>> testres = ibeis.testdata_expts('PZ_MTEST', a=['ctrl::unctrl_comp'])
            >>> ibs = None
            >>> result = testres.print_unique_annot_config_stats(ibs)
            >>> print(result)
        """
        if ibs is None:
            ibs = testres.ibs
        cfx2_dannot_hashid = [ibs.get_annot_hashid_visual_uuid(daids)
                              for daids in testres.cfgx2_daids]
        unique_daids = ut.list_compress(testres.cfgx2_daids,
                                        ut.flag_unique_items(cfx2_dannot_hashid))
        with ut.Indenter('[acfgstats]'):
            print('+====')
            print('Printing %d unique annotconfig stats' % (len(unique_daids)))
            common_acfg = testres.common_acfg
            common_acfg['common'] = ut.dict_filter_nones(common_acfg['common'])
            print('testres.common_acfg = ' + ut.dict_str(common_acfg))
            print('param_basis(len(daids)) = %r' % (
                testres.get_param_basis('len(daids)'),))
            for count, daids in enumerate(unique_daids):
                print('+---')
                print('acfgx = %r/%r' % (count, len(unique_daids)))
                if testres.has_constant_qaids():
                    annotconfig_stats_strs, locals_ = ibs.get_annotconfig_stats(testres.qaids, daids)
                else:
                    ibs.print_annot_stats(daids, prefix='d')
                print('L___')

    def print_results(testres):
        r"""
        CommandLine:
            python -m ibeis --tf TestResult.print_results

        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> from ibeis.expt import experiment_harness
            >>> ibs, testres = experiment_harness.testdata_expts('PZ_MTEST')
            >>> result = testres.print_results()
            >>> print(result)
        """
        from ibeis.expt import experiment_printres
        ibs = testres.ibs
        experiment_printres.print_results(ibs, testres)

    @ut.memoize
    def get_new_hard_qx_list(testres):
        """ Mark any query as hard if it didnt get everything correct """
        rank_mat = testres.get_rank_mat()
        is_new_hard_list = rank_mat.max(axis=1) > 0
        new_hard_qx_list = np.where(is_new_hard_list)[0]
        return new_hard_qx_list

    def get_common_qaids(testres):
        if not testres.has_constant_qaids():
            # Get only cases the tests share for now
            common_qaids = reduce(np.intersect1d, testres.cfgx2_qaids)
            return common_qaids
        else:
            return testres.qaids

    def get_gt_tags(testres):
        ibs = testres.ibs
        truth2_prop, prop2_mat = testres.get_truth2_prop()
        gt_annotmatch_rowids = truth2_prop['gt']['annotmatch_rowid']
        gt_tags = ibs.unflat_map(ibs.get_annotmatch_case_tags, gt_annotmatch_rowids)
        return gt_tags

    def get_gf_tags(testres):
        r"""
        Returns:
            list: case_pos_list

        CommandLine:
            python -m ibeis --tf TestResult.get_gf_tags --db PZ_Master1 --show

        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> from ibeis.init import main_helpers
            >>> ibs, testres = main_helpers.testdata_expts('PZ_Master1', a=['timectrl'])
            >>> filt_cfg = main_helpers.testdata_filtcfg()
            >>> case_pos_list = testres.case_sample2(filt_cfg)
            >>> gf_tags = testres.get_gf_tags()
        """
        ibs = testres.ibs
        truth2_prop, prop2_mat = testres.get_truth2_prop()
        gf_annotmatch_rowids = truth2_prop['gf']['annotmatch_rowid']
        gf_tags = ibs.unflat_map(ibs.get_annotmatch_case_tags, gf_annotmatch_rowids)
        #ibs.unflat_map(ibs.get_annot_case_tags, truth2_prop['gf']['aid'])
        #ibs.unflat_map(ibs.get_annot_case_tags, truth2_prop['gt']['aid'])
        #ibs.get_annot_case_tags(testres.qaids)
        return gf_tags

    def get_all_tags(testres):
        r"""
        CommandLine:
            python -m ibeis --tf TestResult.get_all_tags --db PZ_Master1 --show --filt :
            python -m ibeis --tf TestResult.get_all_tags --db PZ_Master1 --show --filt :min_gf_timedelta=24h
            python -m ibeis --tf TestResult.get_all_tags --db PZ_Master1 --show --filt :min_gf_timedelta=24h,max_gt_rank=5

        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> from ibeis.init import main_helpers
            >>> ibs, testres = main_helpers.testdata_expts('PZ_Master1', a=['timectrl'])
            >>> filt_cfg = main_helpers.testdata_filtcfg()
            >>> case_pos_list = testres.case_sample2(filt_cfg)
            >>> all_tags = testres.get_all_tags()
            >>> selected_tags = ut.list_take(all_tags, case_pos_list.T[0])
            >>> flat_tags = list(map(str, ut.flatten(ut.flatten(selected_tags))))
            >>> print(ut.dict_str(ut.dict_hist(flat_tags), key_order_metric='val'))
            >>> ut.quit_if_noshow()
            >>> import plottool as pt
            >>> pt.word_histogram2(flat_tags, fnum=1, pnum=(1, 2, 1))
            >>> pt.wordcloud(' '.join(flat_tags), fnum=1, pnum=(1, 2, 2))
            >>> pt.set_figtitle(cfghelpers.get_cfg_lbl(filt_cfg))
            >>> ut.show_if_requested()
        """
        gt_tags = testres.get_gt_tags()
        gf_tags = testres.get_gf_tags()
        #gt_tags = [[['gt_' + t for t in tag] for tag in tags] for tags in gt_tags]
        #gf_tags = [[['gf_' + t for t in tag] for tag in tags] for tags in gf_tags]
        #all_tags = [[ut.flatten(t) for t in zip(*item)] for item in zip(gf_tags, gt_tags)]
        all_tags = [ut.list_zipflatten(*item) for item in zip(gf_tags, gt_tags)]
        #from ibeis import tag_funcs
        #ibs.get_annot_case_tags()
        #truth2_prop, prop2_mat = testres.get_truth2_prop()
        #gt_annotmatch_rowids = truth2_prop['gt']['aid']
        #all_tags = [tag_funcs.consolodate_annotmatch_tags(_) for _ in all_tags]
        return all_tags

    def get_gt_annot_tags(testres):
        ibs = testres.ibs
        truth2_prop, prop2_mat = testres.get_truth2_prop()
        gt_annot_tags = ibs.unflat_map(ibs.get_annot_case_tags, truth2_prop['gt']['aid'])
        return gt_annot_tags

    def get_query_annot_tags(testres):
        ibs = testres.ibs
        truth2_prop, prop2_mat = testres.get_truth2_prop()
        #len(testres.cfgx2_qaids)
        unflat_qids = np.tile(testres.qaids[:, None], (len(testres.cfgx2_qaids)))
        query_annot_tags = ibs.unflat_map(ibs.get_annot_case_tags, unflat_qids)
        return query_annot_tags

    def get_gtquery_annot_tags(testres):
        gt_annot_tags = testres.get_gt_annot_tags()
        query_annot_tags = testres.get_query_annot_tags()
        both_tags = [[ut.flatten(t) for t in zip(*item)]
                     for item in zip(query_annot_tags, gt_annot_tags)]
        return both_tags

    def case_sample2(testres, filt_cfg, return_mask=False, verbose=None):
        r"""
        Args:
            filt_cfg (?):

        Returns:
            list: case_pos_list (list of (qx, cfgx)) or isvalid mask

        CommandLine:
            python -m ibeis --tf TestResult.case_sample2
            python -m ibeis --tf TestResult.case_sample2:0
            python -m ibeis --tf TestResult.case_sample2:1 --db PZ_Master1 --filt :min_tags=1
            python -m ibeis --tf TestResult.case_sample2:1 --db PZ_Master1 --filt :min_gf_tags=1

            python -m ibeis --tf TestResult.case_sample2:2 --db PZ_Master1

        Example0:
            >>> # SLOW_DOCTEST
            >>> # The same results is achievable with different filter config settings
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> from ibeis.init import main_helpers
            >>> ibs, testres = main_helpers.testdata_expts('PZ_MTEST', a=['ctrl'])
            >>> filt_cfg1 = {'fail': True}
            >>> case_pos_list1 = testres.case_sample2(filt_cfg1)
            >>> filt_cfg2 = {'min_gtrank': 1}
            >>> case_pos_list2 = testres.case_sample2(filt_cfg2)
            >>> filt_cfg3 = {'min_gtrank': 0}
            >>> case_pos_list3 = testres.case_sample2(filt_cfg3)
            >>> filt_cfg4 = {}
            >>> case_pos_list4 = testres.case_sample2(filt_cfg4)
            >>> assert np.all(case_pos_list1 == case_pos_list2), 'should be equiv configs'
            >>> assert np.any(case_pos_list2 != case_pos_list3), 'should be diff configs'
            >>> assert np.all(case_pos_list3 == case_pos_list4), 'should be equiv configs'

        Example1:
            >>> # SCRIPT
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> from ibeis.init import main_helpers
            >>> ibs, testres = main_helpers.testdata_expts('PZ_MTEST', a=['ctrl'])
            >>> filt_cfg = main_helpers.testdata_filtcfg()
            >>> case_pos_list = testres.case_sample2(filt_cfg)
            >>> result = ('case_pos_list = %s' % (str(case_pos_list),))
            >>> print(result)
            >>> # Extra stuff
            >>> all_tags = testres.get_all_tags()
            >>> selcted_tags = ut.list_take(all_tags, case_pos_list.T[0])
            >>> print('selcted_tags = %r' % (selcted_tags,))

        Example1:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> from ibeis.init import main_helpers
            >>> ibs, testres = main_helpers.testdata_expts('PZ_MTEST', a=['ctrl'])
            >>> filt_cfg = {'fail': True, 'min_gtrank': 1, 'max_gtrank': None, 'min_gf_timedelta': '24h'}
            >>> #filt_cfg = cfghelpers.parse_argv_cfg('--filt')[0]
            >>> case_pos_list = testres.case_sample2(filt_cfg)
            >>> result = ('case_pos_list = %s' % (str(case_pos_list),))
            >>> print(result)
            >>> # Extra stuff
            >>> all_tags = testres.get_all_tags()
            >>> selcted_tags = ut.list_take(all_tags, case_pos_list.T[0])
            >>> print('selcted_tags = %r' % (selcted_tags,))
        """
        if verbose is None:
            verbose = ut.NOT_QUIET

        truth2_prop, prop2_mat = testres.get_truth2_prop()
        # Initialize isvalid flags to all true
        is_valid = np.ones(prop2_mat['is_success'].shape, dtype=np.bool)

        import operator
        from functools import partial

        #common_qaids = testres.get_common_qaids()

        #@ut.memoize
        #def get_num_casetags():
        #    ibs = testres.ibs
        #    #gt_aids = truth2_prop['gt']['aid']
        #    #gf_aids = truth2_prop['gf']['aid']
        #    gt_annotmatch_rowids = truth2_prop['gt']['annotmatch_rowid']
        #    gt_tags = ibs.unflat_map(ibs.get_annotmatch_case_tags, gt_annotmatch_rowids)
        #    num_gt_tags = np.array([list(map(len, _gt_tags)) for _gt_tags in gt_tags])
        #    gf_annotmatch_rowids = truth2_prop['gf']['annotmatch_rowid']

        #    #gt_annotmatch_rowids = [ibs.get_annotmatch_rowid_from_superkey(common_qaids, _gt_aids) for _gt_aids in gt_aids.T]
        #    #gf_annotmatch_rowids = [ibs.get_annotmatch_rowid_from_superkey(common_qaids, _gf_aids) for _gf_aids in gf_aids.T]

        #    gf_tags = ibs.unflat_map(ibs.get_annotmatch_case_tags, gf_annotmatch_rowids)

        #    # get matrix of num tags
        #    num_gf_tags = np.array([list(map(len, _gf_tags)) for _gf_tags in gf_tags])
        #    return num_gt_tags, num_gf_tags

        #def map_num_tags(tags_list):
        #    return np.array([list(map(len, _tags)) for _tags in tags_list])

        #def compare_num_gf_tags(op, val):
        #    num_gf_tags = map_num_tags(testres.get_gf_tags())
        #    return op(num_gf_tags, val)

        #def compare_num_gt_tags(op, val):
        #    num_gt_tags = map_num_tags(testres.get_gt_tags())
        #    return op(num_gt_tags, val)

        #def compare_num_annot_tags(op, val):
        #    num_gt_tags = map_num_tags(testres.get_all_tags())
        #    return op(num_gt_tags, val)

        #def compare_num_tags(op, val):
        #    num_tags = map_num_tags(testres.get_all_tags())
        #    return op(num_tags, val)

        #def in_tags(val, tags_list):
        #    #if '&' in val:
        #    #    logop = all
        #    #    vals = val.split('&')
        #    #elif '|' in val:
        #    #    logop = any
        #    #    vals = val.split('|')
        #    #else:
        #    logop = any
        #    vals = [val]

        #    vals = [v.lower() for v in vals]
        #    lower_tags = [
        #        [[_.lower() for _ in t] for t in tags]
        #        for tags in tags_list]

        #    flags = np.array([
        #        [logop([v in t for v in vals]) for t in tags]
        #        for tags in lower_tags])
        #    return flags

        def unflat_tag_filterflags(tags_list, **kwargs):
            #ut.embed()
            from ibeis import tag_funcs
            flat_tags, cumsum = ut.invertible_flatten2(tags_list)
            flat_flags = tag_funcs.filterflags_general_tags(flat_tags, **kwargs)
            flags = np.array(ut.unflatten2(flat_flags, cumsum))
            return flags

        UTFF = unflat_tag_filterflags

        #def notin_tags(val, tags_list):
        #    return UTFF(tags_list, has_none=val)
        #    #return ~in_tags(val, tags_list)

        #def without_gf_tag(val):
        #    gf_tags = testres.get_gf_tags()
        #    return UTFF(gf_tags, has_none=val)
        #    #flags = notin_tags(val, gf_tags)
        #    #return flags

        #def without_gt_tag(val):
        #    gt_tags = testres.get_gt_tags()
        #    return UTFF(gt_tags, has_none=val)
        #    #flags = notin_tags(val, gt_tags)
        #    #return flags

        #def with_gt_tag(val):
        #    gf_tags = testres.get_gt_tags()
        #    return UTFF(gf_tags, has_any=val)
        #    #flags = in_tags(val, gf_tags)
        #    #return flags

        #def with_gf_tag(val):
        #    gf_tags = testres.get_gf_tags()
        #    return UTFF(gf_tags, has_any=val)
        #    #flags = in_tags(val, gf_tags)
        #    #return flags

        #def with_tag(val):
        #    all_tags = testres.get_all_tags()
        #    return UTFF(all_tags, has_any=val)
        #    #flags = in_tags(val, all_tags)
        #    #return flags

        rule_list = [
            ('fail',     prop2_mat['is_failure']),
            ('success',  prop2_mat['is_success']),
            ('min_gtrank', partial(operator.ge, truth2_prop['gt']['rank'])),
            ('max_gtrank', partial(operator.le, truth2_prop['gt']['rank'])),
            ('max_gtscore', partial(operator.le, truth2_prop['gt']['score'])),
            ('min_gtscore', partial(operator.ge, truth2_prop['gt']['score'])),
            ('min_gf_timedelta', partial(operator.ge, truth2_prop['gf']['timedelta'])),
            ('max_gf_timedelta', partial(operator.le, truth2_prop['gf']['timedelta'])),

            # Tag filtering
            ('min_tags', lambda val: UTFF(testres.get_all_tags(), min_num=val)),
            ('max_tags', lambda val: UTFF(testres.get_all_tags(), max_num=val)),
            ('min_gf_tags', lambda val: UTFF(testres.get_gf_tags(), min_num=val)),
            ('max_gf_tags', lambda val: UTFF(testres.get_gf_tags(), max_num=val)),
            ('min_gt_tags', lambda val: UTFF(testres.get_gt_tags(), min_num=val)),
            ('max_gt_tags', lambda val: UTFF(testres.get_gt_tags(), max_num=val)),

            ('min_query_annot_tags', lambda val: UTFF(testres.get_query_annot_tags(), min_num=val)),
            ('min_gt_annot_tags', lambda val: UTFF(testres.get_gt_annot_tags(), min_num=val)),
            ('min_gtq_tags', lambda val: UTFF(testres.get_gtquery_annot_tags(), min_num=val)),
            ('max_gtq_tags', lambda val: UTFF(testres.get_gtquery_annot_tags(), max_num=val)),

            ('without_gf_tag', lambda val: UTFF(testres.get_gf_tags(), has_none=val)),
            ('without_gt_tag', lambda val: UTFF(testres.get_gt_tags(), has_none=val)),
            ('with_gf_tag', lambda val: UTFF(testres.get_gf_tags(), has_any=val)),
            ('with_gt_tag', lambda val: UTFF(testres.get_gt_tags(), has_any=val)),
            ('with_tag',    lambda val: UTFF(testres.get_all_tags(), has_any=val)),

        ]
        filt_cfg = filt_cfg.copy()

        #timedelta_keys = [
        #    'min_gf_timedelta',
        #    'max_gf_timedelta',
        #]
        #for tdkey in timedelta_keys:

        # hack to convert to seconds
        for tdkey in filt_cfg.keys():
            if tdkey.endswith('_timedelta'):
                filt_cfg[tdkey] = ut.ensure_timedelta(filt_cfg[tdkey])

        if verbose:
            print('[testres] Sampling from is_valid.size=%r with filt=%r' %
                  (is_valid.size, cfghelpers.get_cfg_lbl(filt_cfg)))
            print('  * is_valid.shape = %r' % (is_valid.shape,))

        import copy
        filt_cfg = copy.deepcopy(filt_cfg)

        for key, rule in rule_list:
            val = filt_cfg.pop(key, None)
            if val is not None:
                if isinstance(rule, np.ndarray):
                    # When a rule is an ndarray it must have boolean values
                    flags = rule == val
                else:
                    flags = rule(val)
                if verbose:
                    prev_num_valid = is_valid.sum()
                is_valid = np.logical_and(is_valid, flags)
                if verbose:
                    print('  * is_valid.shape = %r' % (is_valid.shape,))
                    print('SampleRule: %s = %r' % (key, val))
                    num_passed = flags.sum()
                    num_valid = is_valid.sum()
                    print('  * num_passed = %r' % (num_passed,))
                    print('  * prev_num_valid = %r' % (prev_num_valid,))
                    print('  * num_invalided = %r' % (prev_num_valid - num_valid,))
                    print('  * num_valid = %r' % (num_valid,))
        if return_mask:
            return is_valid

        #if False:
        #    # Valid props
        #    gt_ranks = truth2_prop['gt']['rank'][is_valid]
        #    gf_ranks = truth2_prop['gf']['rank'][is_valid]  # NOQA
        #    gt_aids = truth2_prop['gt']['aid'][is_valid]
        #    qaids = testres.get_common_qaids()[np.logical_or.reduce(is_valid.T)]

        qx_list, cfgx_list = np.nonzero(is_valid)

        #    np.vstack((qaids, gt_aids, gt_ranks)).T
        orderby = filt_cfg.pop('orderby', None)
        reverse = filt_cfg.pop('reverse', None)
        sortasc = filt_cfg.pop('sortasc', None)
        sortdsc = filt_cfg.pop('sortdsc', filt_cfg.pop('sortdesc', None))
        if sortdsc is not None:
            assert orderby is None, 'use orderby or sortasc'
            assert reverse is None, 'reverse does not work with sortdsc'
            orderby = sortdsc
            reverse = True
        elif sortasc is not None:
            assert reverse is None, 'reverse does not work with sortasc'
            assert orderby is None, 'use orderby or sortasc'
            orderby = sortasc
            reverse = False
        else:
            reverse = False
        #orderby = filt_cfg.get('orderbydesc', None)
        if orderby is not None:
            if orderby == 'gtscore':
                order_values = truth2_prop['gt']['score']
            elif orderby == 'gfscore':
                order_values = truth2_prop['gf']['score']
            if orderby == 'gtscore':
                order_values = truth2_prop['gt']['score']
            elif orderby == 'gfscore':
                order_values = truth2_prop['gf']['score']
            else:
                if orderby.startswith('gt_'):
                    order_values = truth2_prop['gt'][orderby[3:]]
                elif orderby.startswith('gt'):
                    order_values = truth2_prop['gt'][orderby[2:]]
                elif orderby.startswith('gf_'):
                    order_values = truth2_prop['gt'][orderby[3:]]
                elif orderby.startswith('gf'):
                    order_values = truth2_prop['gt'][orderby[2:]]
                else:
                    raise NotImplementedError('Unknown orerby=%r' % (orderby,))
            flat_order = order_values[is_valid]
            # Flat sorting indeices in a matrix
            if reverse:
                sortx = flat_order.argsort()[::-1]
                #sortx_mat = order_values.flatten().argsort()[::-1].reshape(order_values.shape)
            else:
                sortx = flat_order.argsort()
            #sortx = sortx_mat[is_valid]
            qx_list = qx_list.take(sortx, axis=0)
            cfgx_list = cfgx_list.take(sortx, axis=0)
            # order_values[tuple(case_pos_list.T)]  # assert in order

        index = filt_cfg.pop('index', None)
        if index is not None:
            print('Taking index sample from len(qx_list) = %r' % (len(qx_list),))
            if isinstance(index, six.string_types):
                index = ut.smart_cast(index, slice)
            qx_list = ut.list_take(qx_list, index)
            cfgx_list = ut.list_take(cfgx_list, index)

        ut.delete_keys(filt_cfg, ['_cfgstr', '_cfgindex', '_cfgname', '_cfgtype'])

        if len(filt_cfg) > 0:
            raise NotImplementedError('Unhandled filt_cfg.keys() = %r' % (filt_cfg.keys()))

        case_pos_list = np.vstack((qx_list, cfgx_list)).T
        return case_pos_list

    def case_type_sample(testres, num_per_group=1, with_success=True,
                         with_failure=True, min_success_diff=0):
        category_poses = testres.partition_case_types(min_success_diff=min_success_diff)
        # STRATIFIED SAMPLE OF CASES FROM GROUPS
        #mode = 'failure'
        rng = np.random.RandomState(0)
        ignore_keys = ['total_failure', 'total_success']
        #ignore_keys = []
        #sample_keys = []
        #sample_vals = []
        flat_sample_dict = ut.ddict(list)

        #num_per_group = 1
        modes = []
        if with_success:
            modes += ['success']
        if with_failure:
            modes += ['failure']

        for mode in modes:
            for truth in ['gt', 'gf']:
                type2_poses = category_poses[mode + '_' + truth]
                for key, posses in six.iteritems(type2_poses):
                    if key not in ignore_keys:
                        if num_per_group is not None:
                            sample_posses = ut.random_sample(posses, num_per_group, rng=rng)
                        else:
                            sample_posses = posses

                        flat_sample_dict[mode + '_' + truth + '_' + key].append(sample_posses)

        #list(map(np.vstack, flat_sample_dict.values()))
        sample_keys = flat_sample_dict.keys()
        sample_vals = list(map(np.vstack, flat_sample_dict.values()))

        has_sample = np.array(list(map(len, sample_vals))) > 0
        has_sample_idx = np.nonzero(has_sample)[0]

        print('Unsampled categories = %s' % (
            ut.list_str(ut.list_compress(sample_keys, ~has_sample))))
        print('Sampled categories = %s' % (
            ut.list_str(ut.list_compress(sample_keys, has_sample))))

        sampled_type_list = ut.list_take(sample_keys, has_sample_idx)
        sampled_cases_list = ut.list_take(sample_vals, has_sample_idx)

        sampled_lbl_list = ut.flatten([[lbl] * len(cases)
                                       for lbl, cases in zip(sampled_type_list, sampled_cases_list)])
        if len(sampled_cases_list) == 0:
            return [], []
        sampled_case_list = np.vstack(sampled_cases_list)

        # Computes unique test cases and groups them with all case labels
        caseid_list = vt.compute_unique_data_ids(sampled_case_list)
        unique_case_ids = ut.unique_keep_order2(caseid_list)
        labels_list = ut.dict_take(ut.group_items(sampled_lbl_list, caseid_list), unique_case_ids)
        cases_list = np.vstack(ut.get_list_column(ut.dict_take(ut.group_items(sampled_case_list, caseid_list), unique_case_ids), 0))

        #sampled_case_list = np.vstack(ut.flatten(sample_vals))
        #sampled_case_list = sampled_case_list[vt.unique_row_indexes(case_pos_list)]
        #ut.embed()
        case_pos_list = cases_list
        case_labels_list = labels_list
        #case_pos_list.shape
        #vt.unique_row_indexes(case_pos_list).shape
        return case_pos_list, case_labels_list

    @ut.memoize
    def get_truth2_prop(testres):
        ibs = testres.ibs
        common_qaids = testres.get_common_qaids()
        #common_qaids = ut.random_sample(common_qaids, 20)
        truth2_prop = ut.ddict(ut.odict)

        # TODO: have this function take in a case_pos_list as input instead

        truth2_prop['gt']['aid'] = testres.get_infoprop_mat('qx2_gt_aid', common_qaids)
        truth2_prop['gf']['aid'] = testres.get_infoprop_mat('qx2_gf_aid', common_qaids)
        truth2_prop['gt']['rank'] = testres.get_infoprop_mat('qx2_gt_rank', common_qaids)
        truth2_prop['gf']['rank'] = testres.get_infoprop_mat('qx2_gf_rank', common_qaids)

        truth2_prop['gt']['score'] = np.nan_to_num(testres.get_infoprop_mat('qx2_gt_raw_score', common_qaids))
        truth2_prop['gf']['score'] = np.nan_to_num(testres.get_infoprop_mat('qx2_gf_raw_score', common_qaids))

        # Cast nans to ints
        for truth in ['gt', 'gf']:
            rank_mat = truth2_prop[truth]['rank']
            rank_mat[np.isnan(rank_mat)] = testres.get_worst_possible_rank()
            truth2_prop[truth]['rank'] = rank_mat.astype(np.int)

        # Rank difference
        hardness_degree_rank = truth2_prop['gt']['rank'] - truth2_prop['gf']['rank']
        is_failure = hardness_degree_rank >= 0
        is_success = hardness_degree_rank < 0

        assert np.all(is_success == (truth2_prop['gt']['rank'] == 0))
        #hardness_degree_rank[is_success]
        #is_weird = hardness_degree_rank == 0  # These probably just completely failure spatial verification

        # Get timedelta and annotmatch rowid
        for truth in ['gt', 'gf']:
            aid_mat = truth2_prop[truth]['aid']
            timedelta_mat = np.vstack([
                ibs.get_annot_pair_timdelta(common_qaids, aids)
                for aids in aid_mat.T
            ]).T
            annotmatch_rowid_mat = np.vstack([
                ibs.get_annotmatch_rowid_from_superkey(common_qaids, aids)
                for aids in aid_mat.T
            ]).T
            truth2_prop[truth]['annotmatch_rowid']  = annotmatch_rowid_mat
            truth2_prop[truth]['timedelta'] = timedelta_mat
        prop2_mat = {}
        prop2_mat['is_success'] = is_success
        prop2_mat['is_failure'] = is_failure
        return truth2_prop, prop2_mat

    def partition_case_types(testres, min_success_diff=0):
        """
        Category Definitions
           * Potential nondistinct cases: (probably more a failure to match query keypoints)
               false negatives with rank < 5 with false positives  that have medium score
        """
        # TODO: Make this function divide the failure cases into several types
        # * scenery failure, photobomb failure, matching failure.
        # TODO: Make this function divide success cases into several types
        # * easy success, difficult success, incidental success
        #ut.embed()

        # Matching labels from annotmatch rowid
        truth2_prop, prop2_mat = testres.get_truth2_prop()
        is_success = prop2_mat['is_success']
        is_failure = prop2_mat['is_failure']

        # Which queries differ in success
        min_success_ratio = min_success_diff / (testres.nConfig)
        #qx2_cfgdiffratio = np.array([np.sum(flags) / len(flags) for flags in is_success])
        #qx2_isvalid = np.logical_and((1 - qx2_cfgdiffratio) >= min_success_ratio, min_success_ratio <= min_success_ratio)
        qx2_cfgdiffratio = np.array([
            min(np.sum(flags), len(flags) - np.sum(flags)) / len(flags)
            for flags in is_success])
        qx2_isvalid = qx2_cfgdiffratio >= min_success_ratio
        #qx2_configs_differed = np.array([len(np.unique(flags)) > min_success_diff for flags in is_success])
        #qx2_isvalid = qx2_configs_differed

        ibs = testres.ibs
        type_getters = [
            ibs.get_annotmatch_is_photobomb,
            ibs.get_annotmatch_is_scenerymatch,
            ibs.get_annotmatch_is_hard,
            ibs.get_annotmatch_is_nondistinct,
        ]
        ignore_gt_flags = set(['nondistinct'])
        truth2_is_type = ut.ddict(ut.odict)
        for truth in ['gt', 'gf']:
            annotmatch_rowid_mat = truth2_prop[truth]['annotmatch_rowid']
            # Check which annotmatch rowids are None, they have not been labeled with matching type
            is_unreviewed = np.isnan(annotmatch_rowid_mat.astype(np.float))
            truth2_is_type[truth]['unreviewed'] = is_unreviewed
            for getter_method in type_getters:
                funcname = ut.get_funcname(getter_method)
                key = funcname.replace('get_annotmatch_is_', '')
                if not (truth == 'gt' and key in ignore_gt_flags):
                    is_type = ut.accepts_numpy(getter_method.im_func)(
                        ibs, annotmatch_rowid_mat).astype(np.bool)
                    truth2_is_type[truth][key] = is_type

        truth2_is_type['gt']['cfgxdiffers'] = np.tile(
            (qx2_cfgdiffratio > 0), (testres.nConfig, 1)).T
        truth2_is_type['gt']['cfgxsame']    = ~truth2_is_type['gt']['cfgxdiffers']

        # Make other category information
        gt_rank_ranges = [(5, 50), (50, None), (None, 5)]
        gt_rank_range_keys = []
        for low, high in gt_rank_ranges:
            if low is None:
                rank_range_key = 'rank_under_' + str(high)
                truth2_is_type['gt'][rank_range_key] = truth2_prop['gt']['rank'] < high
            elif high is None:
                rank_range_key = 'rank_above_' + str(low)
                truth2_is_type['gt'][rank_range_key] = truth2_prop['gt']['rank'] >= low
            else:
                rank_range_key = 'rank_between_' + str(low) + '_' + str(high)
                truth2_is_type['gt'][rank_range_key] = np.logical_and(
                    truth2_prop['gt']['rank'] >= low,
                    truth2_prop['gt']['rank'] < high)
            gt_rank_range_keys.append(rank_range_key)

        # Large timedelta ground false cases
        for truth in ['gt', 'gf']:
            truth2_is_type[truth]['large_timedelta'] = truth2_prop[truth]['timedelta'] > 60 * 60
            truth2_is_type[truth]['small_timedelta'] = truth2_prop[truth]['timedelta'] <= 60 * 60

        # Group the positions of the cases into the appropriate categories
        # Success always means that the groundtruth was rank 0
        category_poses = ut.odict()
        for truth in ['gt', 'gf']:
            success_poses = ut.odict()
            failure_poses = ut.odict()
            for key, is_type_ in truth2_is_type[truth].items():
                success_pos_flags = np.logical_and(is_type_, is_success)
                failure_pos_flags = np.logical_and(is_type_, is_failure)
                success_pos_flags = np.logical_and(success_pos_flags, qx2_isvalid[:, None])
                failure_pos_flags = np.logical_and(failure_pos_flags, qx2_isvalid[:, None])
                is_success_pos = np.vstack(np.nonzero(success_pos_flags)).T
                is_failure_pos = np.vstack(np.nonzero(failure_pos_flags)).T
                success_poses[key] = is_success_pos
                failure_poses[key] = is_failure_pos
            # Record totals
            success_poses['total_success'] = np.vstack(np.nonzero(is_success)).T
            failure_poses['total_failure'] = np.vstack(np.nonzero(is_failure)).T
            # Append to parent dict
            category_poses['success_' + truth] = success_poses
            category_poses['failure_' + truth] = failure_poses

        # Remove categories that dont matter
        for rank_range_key in gt_rank_range_keys:
            if not rank_range_key.startswith('rank_under'):
                assert len(category_poses['success_gt'][rank_range_key]) == 0, (
                    'category_poses[\'success_gt\'][%s] = %r' % (
                        rank_range_key,
                        category_poses['success_gt'][rank_range_key],))
            del (category_poses['success_gt'][rank_range_key])

        # Convert to histogram
        #category_hists = ut.odict()
        #for key, pos_dict in category_poses.items():
            #category_hists[key] = ut.map_dict_vals(len, pos_dict)
        #ut.print_dict(category_hists)

        # Split up between different configurations
        if False:
            cfgx2_category_poses = ut.odict()
            for cfgx in range(testres.nConfig):
                cfg_category_poses = ut.odict()
                for key, pos_dict in category_poses.items():
                    cfg_pos_dict = ut.odict()
                    for type_, pos_list in pos_dict.items():
                        #if False:
                        #    _qx2_casegroup = ut.group_items(pos_list, pos_list.T[0], sorted_=False)
                        #    qx2_casegroup = ut.order_dict_by(_qx2_casegroup, ut.unique_keep_order2(pos_list.T[0]))
                        #    grouppos_list = list(qx2_casegroup.values())
                        #    grouppos_len_list = list(map(len, grouppos_list))
                        #    _len2_groupedpos = ut.group_items(grouppos_list, grouppos_len_list, sorted_=False)
                        cfg_pos_list = pos_list[pos_list.T[1] == cfgx]
                        cfg_pos_dict[type_] = cfg_pos_list
                    cfg_category_poses[key] = cfg_pos_dict
                cfgx2_category_poses[cfgx] = cfg_category_poses
            cfgx2_category_hist = ut.hmap_vals(len, cfgx2_category_poses)
            ut.print_dict(cfgx2_category_hist)

        # Print histogram
        # Split up between different configurations
        category_hists = ut.hmap_vals(len, category_poses)
        if ut.NOT_QUIET:
            ut.print_dict(category_hists)

        return category_poses
        #return cfgx2_category_poses
        #% pylab qt4
        #X = gf_timedelta_list[is_failure]
        ##ut.get_stats(X, use_nan=True)
        #X = X[X < 60 * 60 * 24]
        #encoder = vt.ScoreNormalizerUnsupervised(X)
        #encoder.visualize()

        #X = gf_timedelta_list
        #X = X[X < 60 * 60 * 24]
        #encoder = vt.ScoreNormalizerUnsupervised(X)
        #encoder.visualize()

        #X = gt_timedelta_list
        #X = X[X < 60 * 60 * 24]
        #encoder = vt.ScoreNormalizerUnsupervised(X)
        #encoder.visualize()

        #for key, val in key2_gf_is_type.items():
        #    print(val.sum())

    def get_case_positions(testres, mode='failure', disagree_first=True,
                           samplekw=None):
        """
        Helps get failure and success cases

        Args:
            pass

        Returns:
            list: new_hard_qx_list

        CommandLine:
            python -m ibeis --tf TestResult.get_case_positions

        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.test_result import *  # NOQA
            >>> from ibeis.init import main_helpers
            >>> ibs, testres = main_helpers.testdata_expts('PZ_MTEST', a=['uncontrolled'], t=['default:K=[1,2]'])
            >>> mode = 'failure'
            >>> new_hard_qx_list = testres.get_case_positions(mode)
            >>> result = ('new_hard_qx_list = %s' % (str(new_hard_qx_list),))
            >>> print(result)
        """
        common_qaids = testres.get_common_qaids()
        # look at scores of the best gt and gf
        gf_score_mat = testres.get_infoprop_mat('qx2_gf_raw_score', common_qaids)
        gt_score_mat = testres.get_infoprop_mat('qx2_gt_raw_score', common_qaids)
        #gf_score_mat[np.isnan(gf_score_mat)]
        #gt_score_mat[np.isnan(gf_score_mat)]
        # Nan gf scores are easier, Nan gt scores are harder
        gf_score_mat[np.isnan(gf_score_mat)] = 0
        gt_score_mat[np.isnan(gt_score_mat)] = -np.inf

        # Make a degree of hardness
        # TODO: come up with a better measure of hardness
        hardness_degree_mat = gf_score_mat - gt_score_mat

        if False:
            for cfgx in range(len(gt_score_mat.T)):
                encoder = vt.ScoreNormalizer()
                tp_scores = gt_score_mat.T[cfgx]
                tn_scores = gf_score_mat.T[cfgx]
                encoder.fit_partitioned(tp_scores, tn_scores, finite_only=True)
                encoder.visualize()

        qx_list, cfgx_list = np.unravel_index(
            hardness_degree_mat.ravel().argsort()[::-1],
            hardness_degree_mat.shape)
        case_pos_list = np.vstack((qx_list, cfgx_list)).T

        ONLY_FINITE = True
        if ONLY_FINITE:
            flags = np.isfinite(hardness_degree_mat[tuple(case_pos_list.T)])
            case_pos_list = case_pos_list.compress(flags, axis=0)

        # Get list sorted by the easiest hard cases, so we can fix the
        # non-pathological cases first
        if mode == 'failure':
            flags = hardness_degree_mat[tuple(case_pos_list.T)] > 0
            case_pos_list = case_pos_list.compress(flags, axis=0)
        elif mode == 'success':
            flags = hardness_degree_mat[tuple(case_pos_list.T)] < 0
            case_pos_list = case_pos_list.compress(flags, axis=0)
        else:
            raise NotImplementedError('Unknown mode')

        # Group by configuration
        #case_hardness = hardness_degree_mat[tuple(case_pos_list.T)]
        #case_gt_score = gt_score_mat[tuple(case_pos_list.T)]
        #case_gf_score = gf_score_mat[tuple(case_pos_list.T)]

        #hard_degree_list = hardness_degree_mat[tuple(case_pos_list.T)]
        #groupids, groupxs = vt.group_indices(case_pos_list.T[0])
        #groupid2_score = [
        #case_qx_list = ut.unique_keep_order2(case_pos_list.T[0])

        #talk about convoluted
        _qx2_casegroup = ut.group_items(case_pos_list, case_pos_list.T[0], sorted_=False)
        qx2_casegroup = ut.order_dict_by(
            _qx2_casegroup, ut.unique_keep_order2(case_pos_list.T[0]))
        grouppos_list = list(qx2_casegroup.values())
        grouppos_len_list = list(map(len, grouppos_list))
        _len2_groupedpos = ut.group_items(grouppos_list, grouppos_len_list, sorted_=False)
        if samplekw is not None:
            #samplekw_default = {
            #    'per_group': 10,
            #    #'min_intersecting_cfgs': 1,
            #}
            per_group = samplekw['per_group']
            if per_group is not None:
                _len2_groupedpos_keys = list(_len2_groupedpos.keys())
                _len2_groupedpos_values = [
                    groupedpos[::max(1, len(groupedpos) // per_group)]
                    for groupedpos in six.itervalues(_len2_groupedpos)
                ]
                _len2_groupedpos = dict(zip(_len2_groupedpos_keys, _len2_groupedpos_values))
        len2_groupedpos = ut.map_dict_vals(np.vstack, _len2_groupedpos)

        #percentile_stratify
        #def percentile_stratified_sample(x, num, rng=np.random):
        #    hardness = hardness_degree_mat[tuple(x.T)]
        #    percentiles = np.percentile(hardness, [0, 25, 50, 75, 100])
        #    percentiles[-1] += 1
        #    groups = [x.compress(np.logical_and(low <= hardness, hardness < high), axis=0) for low, high in ut.iter_window(percentiles)]
        #    [ut.random_sample(group, num, rng=rng) for group in groups]

        #ut.print_dict(len2_groupedpos, nl=2)
        if disagree_first:
            unflat_pos_list = list(len2_groupedpos.values())
        else:
            unflat_pos_list = list(len2_groupedpos.values()[::-1])
        case_pos_list = vt.safe_vstack(unflat_pos_list, (0, 2), np.int)
        return case_pos_list

    def get_interesting_ranks(test_results):
        """ find the rows that vary greatest with the parameter settings """
        rank_mat = test_results.get_rank_mat()
        # Find rows which scored differently over the various configs FIXME: duplicated
        isdiff_flags = [not np.all(row == row[0]) for row in rank_mat]
        #diff_aids    = ut.list_compress(test_results.qaids, isdiff_flags)
        diff_rank    = rank_mat.compress(isdiff_flags, axis=0)
        diff_qxs     = np.where(isdiff_flags)[0]
        if False:
            rankcategory = np.log(diff_rank + 1)
        else:
            rankcategory = diff_rank.copy()
            rankcategory[diff_rank == 0]  = 0
            rankcategory[diff_rank > 0]   = 1
            rankcategory[diff_rank > 2]   = 2
            rankcategory[diff_rank > 5]   = 3
            rankcategory[diff_rank > 50]  = 4
            rankcategory[diff_rank > 100] = 5
        row_rankcategory_std = np.std(rankcategory, axis=1)
        row_rankcategory_mean = np.mean(rankcategory, axis=1)
        import vtool as vt
        row_sortx = vt.argsort_multiarray(
            [row_rankcategory_std, row_rankcategory_mean], reverse=True)
        interesting_qx_list = diff_qxs.take(row_sortx).tolist()
        #print("INTERSETING MEASURE")
        #print(interesting_qx_list)
        #print(row_rankcategory_std)
        #print(ut.list_take(qaids, row_sortx))
        #print(diff_rank.take(row_sortx, axis=0))
        return interesting_qx_list

    def interact_individual_result(testres, qaid, cfgx=0):
        #qaids = testres.get_common_qaids()
        ibs = testres.ibs
        cfgx_list = ut.ensure_iterable(cfgx)
        qreq_list = ut.list_take(testres.cfgx2_qreq_, cfgx_list)
        # Preload any requested configs
        qres_list = [qreq_.load_cached_qres(qaid) for qreq_ in qreq_list]
        cfgx2_shortlbl = testres.get_short_cfglbls()
        show_kwargs = {
            'N': 3,
            'ori': True,
            'ell_alpha': .9,
        }
        # SHOW ANALYSIS
        show_kwargs['show_query'] = False
        show_kwargs['viz_name_score'] = True
        show_kwargs['show_timedelta'] = True
        show_kwargs['show_gf'] = True
        show_kwargs['with_figtitle'] = False
        for cfgx, qres, qreq_ in zip(cfgx_list, qres_list, qreq_list):
            query_lbl = cfgx2_shortlbl[cfgx]
            fnum = cfgx
            qres.ishow_analysis(
                ibs, figtitle=query_lbl, fnum=fnum, annot_mode=1, qreq_=qreq_,
                **show_kwargs)

    def reconstruct_test_flags(testres):
        if '_cfgstr' in testres.common_cfgdict:
            pipecfg_args = [testres.common_cfgdict['_cfgstr']]
        else:
            pipecfg_args = ut.unique_keep_order2(
                [cfg['_cfgstr'] for cfg in testres.varied_cfg_list])

        if '_cfgstr' in testres.common_acfg['common']:
            annotcfg_args = [testres.common_acfg['common']['_cfgstr']]
        else:
            annotcfg_args = ut.unique_keep_order2([
                acfg['common']['_cfgstr']
                for acfg in testres.varied_acfg_list])
        flagstr =  ' '.join([
            '-a ' + ' '.join(annotcfg_args),
            '-t ' + ' ' .join(pipecfg_args),
            '--db ' + testres.ibs.get_dbname()
        ])
        return flagstr

    def draw_rank_cdf(testres):
        from ibeis.expt import experiment_drawing
        experiment_drawing.draw_rank_cdf(testres.ibs, testres)

    def find_score_thresh_cutoff(testres):
        """
        FIXME
        DUPLICATE CODE
        rectify with experiment_drawing
        """
        #import plottool as pt
        import vtool as vt
        if ut.VERBOSE:
            print('[dev] annotationmatch_scores')
        #from ibeis.expt import cfghelpers

        assert len(testres.cfgx2_qreq_) == 1, 'can only specify one config here'
        cfgx = 0
        #qreq_ = testres.cfgx2_qreq_[cfgx]
        common_qaids = testres.get_common_qaids()
        gt_rawscore = testres.get_infoprop_mat('qx2_gt_raw_score').T[cfgx]
        gf_rawscore = testres.get_infoprop_mat('qx2_gf_raw_score').T[cfgx]

        # FIXME: may need to specify which cfg is used in the future
        #isvalid = testres.case_sample2(filt_cfg, return_mask=True).T[cfgx]

        tp_nscores = gt_rawscore
        tn_nscores = gf_rawscore
        tn_qaids = tp_qaids = common_qaids
        #encoder = vt.ScoreNormalizer(target_tpr=.7)
        #print(qreq_.get_cfgstr())
        part_attrs = {1: {'qaid': tp_qaids},
                      0: {'qaid': tn_qaids}}

        fpr = None
        tpr = .85
        encoder = vt.ScoreNormalizer(adjust=8, fpr=fpr, tpr=tpr, monotonize=True)
        #tp_scores = tp_nscores
        #tn_scores = tn_nscores
        name_scores, labels, attrs = encoder._to_xy(tp_nscores, tn_nscores, part_attrs)
        encoder.fit(name_scores, labels, attrs)
        #score_thresh = encoder.learn_threshold()
        score_thresh = encoder.learn_threshold2()

        # Find intersection point
        # TODO: add to score normalizer.
        # Improve robustness
        #pt.figure()
        #pt.plot(xdata, curve)
        #pt.plot(x_submax, y_submax, 'o')
        return score_thresh

    def print_percent_identification_success(testres):
        """
        Example:
            >>> # DISABLE_DOCTEST
            >>> from ibeis.expt.experiment_drawing import *  # NOQA
        """
        ibs = testres.ibs
        unique_nids, groupxs = vt.group_indices(ibs.get_annot_nids(testres.qaids))
        testres.cfgx2_cfgresinfo[0].keys()
        #rankmat = testres.get_rank_mat()
        qx2_gt_raw_score = testres.get_infoprop_mat('qx2_gt_raw_score')
        qx2_gf_raw_score = testres.get_infoprop_mat('qx2_gf_raw_score')
        nx2_gt_raw_score = np.array([
            ut.safe_max(scores)
            for scores in vt.apply_grouping(qx2_gt_raw_score, groupxs)])
        nx2_gf_raw_score = np.array([
            ut.safe_max(scores)
            for scores in vt.apply_grouping(qx2_gf_raw_score, groupxs)])

        success = nx2_gt_raw_score > nx2_gf_raw_score
        print('success = %r / %r = %r' % (
            success.sum(), len(success), success.sum() / len(success)))


if __name__ == '__main__':
    """
    CommandLine:
        python -m ibeis.expt.test_result
        python -m ibeis.expt.test_result --allexamples
        python -m ibeis.expt.test_result --allexamples --noface --nosrc
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()