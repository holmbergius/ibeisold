# -*- coding: utf-8 -*-
"""
Oxford Experiment:
    ibeis TestResult --db Oxford -p smk:nWords=[64000],nAssign=[1],SV=[False],can_match_sameimg=True -a oxford
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import dtool
import six
import utool as ut
import numpy as np
from ibeis.algo.smk import match_chips5 as mc5
from ibeis.algo.smk import vocab_indexer
from ibeis.algo.smk import inverted_index
from ibeis.algo.smk import smk_funcs
from ibeis import core_annots
from ibeis.algo import Config as old_config
(print, rrr, profile) = ut.inject2(__name__)


class MatchHeuristicsConfig(dtool.Config):
    _param_info_list = [
        ut.ParamInfo('can_match_self', False),
        ut.ParamInfo('can_match_samename', True),
        ut.ParamInfo('can_match_sameimg', False),
    ]


class SMKRequestConfig(dtool.Config):
    """ Figure out how to do this """
    _param_info_list = [
        ut.ParamInfo('proot', 'smk'),
        ut.ParamInfo('smk_alpha', 3.0),
        ut.ParamInfo('smk_thresh', 0.0),
        #ut.ParamInfo('smk_thresh', -1.0),
        ut.ParamInfo('agg', True),
        ut.ParamInfo('data_ma', False),  # hack for query only multiple assignment
        ut.ParamInfo('word_weight_method', 'idf', 'wwm'),  # hack for query only multiple assignment
        ut.ParamInfo('smk_version', 3),
    ]
    _sub_config_list = [
        core_annots.ChipConfig,
        core_annots.FeatConfig,
        old_config.SpatialVerifyConfig,
        vocab_indexer.VocabConfig,
        inverted_index.InvertedIndexConfig,
        MatchHeuristicsConfig,
    ]


@ut.reloadable_class
class SMKRequest(mc5.EstimatorRequest):
    r"""
    qreq_-like object. Trying to work on becoming more scikit-ish

    CommandLine:
        python -m ibeis.algo.smk.smk_pipeline SMKRequest --profile
        python -m ibeis.algo.smk.smk_pipeline SMKRequest --show

        python -m ibeis draw_rank_cdf --db GZ_ALL --show \
            -p :proot=smk,num_words=[64000,4000],nAssign=[1,5],sv_on=[False,True] \
            -a ctrl:qmingt=2

        python -m ibeis draw_rank_cdf --db PZ_MTEST --show \
            -p :proot=smk,num_words=[64000,8000,4000],nAssign=[1,2,4],sv_on=[True,False] \
                default:proot=vsmany,sv_on=[True,False] \
            -a default:qmingt=2

        python -m ibeis draw_rank_cdf --db PZ_MTEST --show \
            -p :proot=smk,num_words=[64000],nAssign=[1],sv_on=[True] \
                default:proot=vsmany,sv_on=[True] \
            -a default:qmingt=2

        python -m ibeis draw_rank_cdf --db PZ_Master1 --show \
            -p :proot=smk,num_words=[64000],nAssign=[1],sv_on=[False] \
            -a ctrl:qmingt=2

        python -m ibeis draw_rank_cdf --db PZ_Master1 \
            -p :proot=smk,num_words=[64000],nAssign=[1],sv_on=[True] \
            -a ctrl:qmingt=2,qindex=60:80 --profile

        python -m ibeis draw_rank_cdf --db GZ_ALL \
            -p :proot=smk,num_words=[64000],nAssign=[1],sv_on=[True] \
            -a ctrl:qmingt=2,qindex=40:60 --profile

    Example:
        >>> from ibeis.algo.smk.smk_pipeline import *  # NOQA
        >>> import ibeis
        >>> ibs, aid_list = ibeis.testdata_aids(defaultdb='PZ_MTEST')
        >>> qaids = aid_list[0:2]
        >>> daids = aid_list[:]
        >>> config = {'nAssign': 2, 'num_words': 64000, 'sv_on': True}
        >>> qreq_ = SMKRequest(ibs, qaids, daids, config)
        >>> qreq_.ensure_data()
        >>> cm_list = qreq_.execute()
        >>> ut.quit_if_noshow()
        >>> ut.qt4ensure()
        >>> cm_list[0].ishow_analysis(qreq_, fnum=1, viz_name_score=False)
        >>> cm_list[1].ishow_analysis(qreq_, fnum=2, viz_name_score=False)
        >>> ut.show_if_requested()

    """
    def __init__(qreq_, ibs=None, qaids=None, daids=None, config=None):
        super(SMKRequest, qreq_).__init__()
        if config is None:
            config = {}

        qreq_.ibs = ibs
        qreq_.qaids = qaids
        qreq_.daids = daids

        qreq_.config = config

        #qreq_.vocab = None
        #qreq_.dinva = None

        qreq_.qinva = None
        qreq_.dinva = None
        qreq_.smk = SMK()

        # Hack to work with existing hs code
        qreq_.stack_config = SMKRequestConfig(**config)
        # Flat config
        qreq_.qparams = dtool.base.StackedConfig([
            dict(qreq_.stack_config.parse_items())
        ])
        #    # TODO: add vocab, inva, features
        qreq_.cachedir = ut.ensuredir((ibs.cachedir, 'smk'))

    def ensure_data(qreq_):
        """
            >>> import ibeis
            >>> qreq_ = ibeis.testdata_qreq_(defaultdb='Oxford', a='oxford',
            >>>                              p='default:proot=smk,nAssign=1,num_words=64000,sv_on=False')
        """
        print('Ensure data for %s' % (qreq_,))

        memtrack = ut.MemoryTracker(disable=True)
        #qreq_.cachedir = ut.ensuredir((ibs.cachedir, 'smk'))
        qreq_.ensure_nids()

        def make_cacher(name, cfgstr=None):
            if cfgstr is None:
                cfgstr = ut.hashstr27(qreq_.get_cfgstr())
            if False and ut.is_developer():
                return ut.Cacher(
                    fname=name + '_' + qreq_.ibs.get_dbname(),
                    cfgstr=cfgstr,
                    cache_dir=ut.ensuredir(ut.truepath('~/Desktop/smkcache'))
                )
            else:
                wrp = ut.DynStruct()
                def ensure(func):
                    return func()
                wrp.ensure = ensure
                return wrp

        import copy
        dconfig = copy.deepcopy(qreq_.qparams)
        qconfig = qreq_.qparams
        if qreq_.qparams['data_ma']:
            # Disable database-dise multi-assignment
            dconfig['nAssign'] = 1

        depc = qreq_.ibs.depc
        vocab_aids = qreq_.daids

        depc = qreq_.ibs.depc
        dinva_pcfgstr = depc.stacked_config(
            None, 'inverted_agg_assign', config=dconfig).get_cfgstr()
        qinva_pcfgstr = depc.stacked_config(
            None, 'inverted_agg_assign', config=qconfig).get_cfgstr()
        dannot_vuuid = qreq_.ibs.get_annot_hashid_visual_uuid(qreq_.daids).strip('_')
        qannot_vuuid = qreq_.ibs.get_annot_hashid_visual_uuid(qreq_.qaids).strip('_')
        tannot_vuuid = dannot_vuuid
        dannot_suuid = qreq_.ibs.get_annot_hashid_semantic_uuid(qreq_.daids).strip('_')
        qannot_suuid = qreq_.ibs.get_annot_hashid_semantic_uuid(qreq_.qaids).strip('_')

        dinva_phashid = ut.hashstr27(dinva_pcfgstr + tannot_vuuid)
        qinva_phashid = ut.hashstr27(qinva_pcfgstr + tannot_vuuid)
        dinva_cfgstr = '_'.join([dannot_vuuid, dinva_phashid])
        qinva_cfgstr = '_'.join([qannot_vuuid, qinva_phashid])

        wwm = qreq_.qparams['word_weight_method']

        #vocab = inverted_index.new_load_vocab(ibs, qreq_.daids, config)
        dinva_cacher = make_cacher('inva', dinva_cfgstr)
        qinva_cacher = make_cacher('inva', qinva_cfgstr)
        dwwm_cacher  = make_cacher('word_weight', wwm + dinva_cfgstr)

        gamma_phashid = ut.hashstr27(qreq_.get_pipe_cfgstr() + tannot_vuuid)
        dgamma_cfgstr = '_'.join([dannot_suuid, gamma_phashid])
        qgamma_cfgstr = '_'.join([qannot_suuid, gamma_phashid])
        dgamma_cacher = make_cacher('dgamma', cfgstr=dgamma_cfgstr)
        qgamma_cacher = make_cacher('qgamma', cfgstr=qgamma_cfgstr)

        memtrack.report()

        dinva = dinva_cacher.ensure(
            lambda: inverted_index.InvertedAnnots.from_depc(
                depc, qreq_.daids, vocab_aids, dconfig))

        memtrack.report()

        qinva = qinva_cacher.ensure(
            lambda: inverted_index.InvertedAnnots.from_depc(
                depc, qreq_.qaids, vocab_aids, qconfig))

        memtrack.report()

        dinva.wx_to_aids = dinva.compute_inverted_list()
        memtrack.report()

        wx_to_weight = dwwm_cacher.ensure(
            lambda: dinva.compute_word_weights(wwm))
        dinva.wx_to_weight = wx_to_weight
        qinva.wx_to_weight = wx_to_weight
        memtrack.report()

        thresh = qreq_.qparams['smk_thresh']
        alpha = qreq_.qparams['smk_alpha']

        dinva.gamma_list = dgamma_cacher.ensure(
            lambda: dinva.compute_gammas(alpha, thresh))
        memtrack.report()

        qinva.gamma_list = qgamma_cacher.ensure(
            lambda: qinva.compute_gammas(alpha, thresh))
        memtrack.report()

        qreq_.qinva = qinva
        qreq_.dinva = dinva

        print('loading keypoints')
        if qreq_.qparams.sv_on:
            qreq_.data_kpts = qreq_.ibs.get_annot_kpts(
                qreq_.daids, config2_=qreq_.extern_data_config2)
        memtrack.report()

        print('building aid index')
        qreq_.daid_to_didx = ut.make_index_lookup(qreq_.daids)
        memtrack.report()

    def execute_pipeline(qreq_):
        """
        >>> from ibeis.algo.smk.smk_pipeline import *  # NOQA
        >>> ibs, smk, qreq_ = testdata_smk()
        >>> cm_list = qreq_.execute()
        """
        smk = qreq_.smk
        cm_list = smk.predict_matches(qreq_)
        return cm_list

    def get_qreq_qannot_kpts(qreq_, qaids):
        return qreq_.ibs.get_annot_kpts(
            qaids, config2_=qreq_.extern_query_config2)

    def get_qreq_dannot_kpts(qreq_, daids):
        didx_list = ut.take(qreq_.daid_to_didx, daids)
        return ut.take(qreq_.data_kpts, didx_list)
        #return qreq_.ibs.get_annot_kpts(
        #    daids, config2_=qreq_.extern_data_config2)


@ut.reloadable_class
class SMK(ut.NiceRepr):
    """
    Harness class that controls the execution of the SMK algorithm

    K(X, Y) = gamma(X) * gamma(Y) * sum([Mc(Xc, Yc) for c in words])
    """

    def predict_matches(smk, qreq_, verbose=True):
        """
        >>> from ibeis.algo.smk.smk_pipeline import *  # NOQA
        >>> ibs, smk, qreq_ = testdata_smk()
        >>> verbose = True
        """
        print('Predicting matches')
        #assert qreq_.qinva.vocab is qreq_.dinva.vocab
        #X_list = qreq_.qinva.inverted_annots(qreq_.qaids)
        #Y_list = qreq_.dinva.inverted_annots(qreq_.daids)
        #verbose = 2
        _prog = ut.ProgPartial(lbl='smk query', bs=verbose <= 1, enabled=verbose)
        daids = np.array(qreq_.daids)
        cm_list = [smk.match_single(qaid, daids, qreq_, verbose=verbose > 1)
                   for qaid in _prog(qreq_.qaids)]
        return cm_list

    @profile
    def match_single(smk, qaid, daids, qreq_, verbose=True):
        """
        CommandLine:
            python -m ibeis.algo.smk.smk_pipeline SMK.match_single --profile
            python -m ibeis.algo.smk.smk_pipeline SMK.match_single --show

            python -m ibeis SMK.match_single -a ctrl:qmingt=2 --profile --db PZ_Master1
            python -m ibeis SMK.match_single -a ctrl --profile --db GZ_ALL

        Example:
            >>> # FUTURE_ENABLE
            >>> from ibeis.algo.smk.smk_pipeline import *  # NOQA
            >>> import ibeis
            >>> qreq_ = ibeis.testdata_qreq_(defaultdb='PZ_MTEST')
            >>> ibs = qreq_.ibs
            >>> daids = qreq_.daids
            >>> #ibs, daids = ibeis.testdata_aids(defaultdb='PZ_MTEST', default_set='dcfg')
            >>> qreq_ = SMKRequest(ibs, daids[0:1], daids, {'agg': True,
            >>>                                             'num_words': 1000,
            >>>                                             'sv_on': True})
            >>> qreq_.ensure_data()
            >>> qaid = qreq_.qaids[0]
            >>> daids = qreq_.daids
            >>> daid = daids[1]
            >>> verbose = True
            >>> cm = qreq_.smk.match_single(qaid, daids, qreq_)
            >>> ut.quit_if_noshow()
            >>> ut.qt4ensure()
            >>> cm.ishow_analysis(qreq_)
            >>> ut.show_if_requested()
        """
        from ibeis.algo.hots import chip_match
        from ibeis.algo.hots import pipeline

        alpha  = qreq_.qparams['smk_alpha']
        thresh = qreq_.qparams['smk_thresh']
        agg    = qreq_.qparams['agg']
        #nAnnotPerName   = qreq_.qparams.nAnnotPerNameSVER

        sv_on   = qreq_.qparams.sv_on
        if sv_on:
            nNameShortList  = qreq_.qparams.nNameShortlistSVER
            shortsize = nNameShortList
        else:
            shortsize = None

        X = qreq_.qinva.get_annot(qaid)

        # Determine which database annotations need to be checked
        #with ut.Timer('searching qaid=%r' % (qaid,), verbose=verbose):
        hit_inva_wxs = ut.take(qreq_.dinva.wx_to_aids, X.wx_list)
        hit_daids = np.array(list(set(ut.iflatten(hit_inva_wxs))))

        # Mark impossible daids
        #with ut.Timer('checking impossible daids=%r' % (qaid,), verbose=verbose):
        valid_flags = check_can_match(qaid, hit_daids, qreq_)
        valid_daids = hit_daids.compress(valid_flags)

        shortlist = ut.Shortlist(shortsize)
        #gammaX = smk.gamma(X, wx_to_weight, agg, alpha, thresh)
        _prog = ut.ProgPartial(lbl='smk scoring qaid=%r' % (qaid,),
                               enabled=verbose, bs=True, adjust=True)

        wx_to_weight = qreq_.dinva.wx_to_weight

        debug = False
        if debug:
            qnid = qreq_.get_qreq_annot_nids([qaid])[0]
            daids = np.array(qreq_.daids)
            dnids = qreq_.get_qreq_annot_nids(daids)
            correct_aids = daids[np.where(dnids == qnid)[0]]
            daid = correct_aids[0]

        if agg:
            for daid in _prog(valid_daids):
                Y = qreq_.dinva.get_annot(daid)
                item = match_kernel_agg(X, Y, wx_to_weight, alpha, thresh)
                shortlist.insert(item)
        else:
            for daid in _prog(valid_daids):
                Y = qreq_.dinva.get_annot(daid)
                item = match_kernel_sep(X, Y, wx_to_weight, alpha, thresh)
                shortlist.insert(item)

        # Build chipmatches for the shortlist results

        #with ut.Timer('build cms', verbose=verbose):
        cm = chip_match.ChipMatch(qaid=qaid, fsv_col_lbls=['smk'])
        cm.daid_list = []
        cm.fm_list = []
        cm.fsv_list = []
        _prog = ut.ProgPartial(lbl='smk build cm qaid=%r' % (qaid,),
                               enabled=verbose, bs=True, adjust=True)
        for item in _prog(shortlist):
            (score, score_list, Y, X_idx, Y_idx) = item
            X_fxs = ut.take(X.fxs_list, X_idx)
            Y_fxs = ut.take(Y.fxs_list, Y_idx)
            # Only build matches for those that sver will use
            if agg:
                X_maws = ut.take(X.maws_list, X_idx)
                Y_maws = ut.take(Y.maws_list, Y_idx)
                fm, fs = smk_funcs.build_matches_agg(X_fxs, Y_fxs, X_maws,
                                                     Y_maws, score_list)
            else:
                fm, fs = smk_funcs.build_matches_sep(X_fxs, Y_fxs, score_list)
            if len(fm) > 0:
                #assert not np.any(np.isnan(fs))
                daid = Y.aid
                fsv = fs[:, None]
                cm.daid_list.append(daid)
                cm.fm_list.append(fm)
                cm.fsv_list.append(fsv)
        cm._update_daid_index()
        cm.arraycast_self()
        cm.score_maxcsum(qreq_)

        #if False:
        #    cm.assert_self(qreq_=qreq_, verbose=True)

        if sv_on:
            cm = pipeline.sver_single_chipmatch(qreq_, cm, verbose=verbose)
            cm.score_maxcsum(qreq_)

        return cm


def word_isect(X, Y, wx_to_weight):
    isect_words = sorted(X.words.intersection(Y.words))
    X_idx = ut.take(X.wx_to_idx, isect_words)
    Y_idx = ut.take(Y.wx_to_idx, isect_words)
    weights = ut.take(wx_to_weight, isect_words)
    return X_idx, Y_idx, weights


def match_kernel_agg(X, Y, wx_to_weight, alpha, thresh):
    gammaXY = X.gamma * Y.gamma
    # Words in common define matches
    X_idx, Y_idx, weights = word_isect(X, Y, wx_to_weight)

    PhisX, flagsX = X.Phis_flags(X_idx)
    PhisY, flagsY = Y.Phis_flags(Y_idx)
    score_list = smk_funcs.match_scores_agg(
        PhisX, PhisY, flagsX, flagsY, alpha, thresh)

    norm_weights = (weights * gammaXY)
    score_list *= norm_weights
    score = score_list.sum()
    item = (score, score_list, Y, X_idx, Y_idx)
    return item


def match_kernel_sep(X, Y, wx_to_weight, alpha, thresh):
    gammaXY = X.gamma * Y.gamma
    # Words in common define matches
    X_idx, Y_idx, weights = word_isect(X, Y, wx_to_weight)

    phisX_list, flagsY_list = X.phis_flags_list(X_idx)
    phisY_list, flagsX_list = Y.phis_flags_list(Y_idx)
    scores_list = smk_funcs.match_scores_sep(
        phisX_list, phisY_list, flagsX_list, flagsY_list, alpha,
        thresh)

    norm_weights = (weights * gammaXY)
    for scores, w in zip(scores_list, norm_weights):
        scores *= w

    score = [s.sum() for s in scores_list].sum()
    item = (score, scores_list, Y, X_idx, Y_idx)
    return item


def check_can_match(qaid, hit_daids, qreq_):
    can_match_samename = qreq_.qparams.can_match_samename
    can_match_sameimg = qreq_.qparams.can_match_sameimg
    can_match_self = False
    valid_flags = np.ones(len(hit_daids), dtype=np.bool)
    # Check that the two annots meet the conditions
    if not can_match_self:
        valid_flags[hit_daids == qaid] = False
    if not can_match_samename:
        qnid = qreq_.get_qreq_annot_nids([qaid])[0]
        hit_dnids = qreq_.get_qreq_annot_nids(hit_daids)
        valid_flags[hit_dnids == qnid] = False
    if not can_match_sameimg:
        qgid = qreq_.get_qreq_annot_gids([qaid])[0]
        hit_dgids = qreq_.get_qreq_annot_gids(hit_daids)
        valid_flags[hit_dgids == qgid] = False
    return valid_flags


def testdata_smk(*args, **kwargs):
    """
    >>> from ibeis.algo.smk.smk_pipeline import *  # NOQA
    >>> kwargs = {}
    """
    import ibeis
    import sklearn
    import sklearn.cross_validation
    # import sklearn.model_selection
    ibs, aid_list = ibeis.testdata_aids(defaultdb='PZ_MTEST')
    nid_list = np.array(ibs.annots(aid_list).nids)
    rng = ut.ensure_rng(0)
    xvalkw = dict(n_folds=4, shuffle=False, random_state=rng)

    skf = sklearn.cross_validation.StratifiedKFold(nid_list, **xvalkw)
    train_idx, test_idx = six.next(iter(skf))
    daids = ut.take(aid_list, train_idx)
    qaids = ut.take(aid_list, test_idx)

    config = {
        'num_words': 1000,
    }
    config.update(**kwargs)
    qreq_ = SMKRequest(ibs, qaids, daids, config)
    smk = qreq_.smk
    #qreq_ = ibs.new_query_request(qaids, daids, cfgdict={'pipeline_root': 'smk', 'proot': 'smk'})
    #qreq_ = ibs.new_query_request(qaids, daids, cfgdict={})
    return ibs, smk, qreq_


if __name__ == '__main__':
    r"""
    CommandLine:
        export PYTHONPATH=$PYTHONPATH:/home/joncrall/code/ibeis/ibeis/algo/smk
        python ~/code/ibeis/ibeis/algo/smk/smk_pipeline.py
        python ~/code/ibeis/ibeis/algo/smk/smk_pipeline.py --allexamples
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()