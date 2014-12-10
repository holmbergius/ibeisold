from __future__ import absolute_import, division, print_function
#import ibeis
import six
import utool as ut
#import numpy as np
#import functools
from six.moves import input, filter  # NOQA
print, print_, printDBG, rrr, profile = ut.inject(__name__, '[inchelp]')


def assert_annot_consistency(ibs1, ibs2, aid_list1, aid_list2):
    """
    just tests uuids

    if anything goes wrong this should fix it:
        ibs1.update_annot_visual_uuids(aid_list1)
        ibs2.update_annot_visual_uuids(aid_list2)
        ibsfuncs.fix_remove_visual_dupliate_annotations(ibs1)
    """
    assert len(aid_list2) == len(aid_list1)
    visualtup1 = ibs1.get_annot_visual_uuid_info(aid_list1)
    visualtup2 = ibs2.get_annot_visual_uuid_info(aid_list2)

    _visual_uuid_list1 = [ut.augment_uuid(*tup) for tup in zip(*visualtup1)]
    _visual_uuid_list2 = [ut.augment_uuid(*tup) for tup in zip(*visualtup2)]

    assert ut.hashstr(visualtup1) == ut.hashstr(visualtup2)
    ut.assert_lists_eq(visualtup1[0], visualtup2[0])
    ut.assert_lists_eq(visualtup1[1], visualtup2[1])
    ut.assert_lists_eq(visualtup1[2], visualtup2[2])
    #semantic_uuid_list1 = ibs1.get_annot_semantic_uuids(aid_list1)
    #semantic_uuid_list2 = ibs2.get_annot_semantic_uuids(aid_list2)

    visual_uuid_list1 = ibs1.get_annot_visual_uuids(aid_list1)
    visual_uuid_list2 = ibs2.get_annot_visual_uuids(aid_list2)

    # make sure visual uuids are still determenistic
    ut.assert_lists_eq(visual_uuid_list1, visual_uuid_list2)
    ut.assert_lists_eq(_visual_uuid_list1, visual_uuid_list1)
    ut.assert_lists_eq(_visual_uuid_list2, visual_uuid_list2)

    ibs1_dup_annots = ut.debug_duplicate_items(visual_uuid_list1)
    ibs2_dup_annots = ut.debug_duplicate_items(visual_uuid_list2)

    # if these fail try ibsfuncs.fix_remove_visual_dupliate_annotations
    assert len(ibs1_dup_annots) == 0
    assert len(ibs2_dup_annots) == 0


def ensure_clean_data(ibs1, ibs2, aid_list1, aid_list2):
    """
    removes previously set names and exemplars
    """
    # Make sure that there are not any names in this database
    nid_list2 = ibs2.get_annot_name_rowids(aid_list2, distinguish_unknowns=False)
    if not ut.list_all_eq_to(nid_list2, 0):
        print('Removing names from database')
        ibs2.set_annot_name_rowids(aid_list2, [ibs2.UNKNOWN_NAME_ROWID] * len(aid_list2))

    #exemplarflag_list2 = ibs2.get_annot_exemplar_flags(aid_list2)
    #if not ut.list_all_eq_to(exemplarflag_list2, 0):
    print('Unsetting all exemplars from database')
    ibs2.set_annot_exemplar_flags(aid_list2, [False] * len(aid_list2))

    # this test is for plains
    #assert  ut.list_all_eq_to(ibs2.get_annot_species(aid_list2), 'zebra_plains')
    ibs2.delete_invalid_nids()


def annot_consistency_checks(ibs1, ibs2, aid_list1, aid_list2):
    try:
        assert_annot_consistency(ibs1, ibs2, aid_list1, aid_list2)
    except Exception as ex:
        # update and try again on failure
        ut.printex(ex, ('warning: consistency check failed.'
                        'updating and trying once more'), iswarning=True)
        ibs1.update_annot_visual_uuids(aid_list1)
        ibs2.update_annot_visual_uuids(aid_list2)
        assert_annot_consistency(ibs1, ibs2, aid_list1, aid_list2)
    ensure_clean_data(ibs1, ibs2, aid_list1, aid_list2)


def get_oracle_decision(metatup, qaid, sorted_nids, sorted_aids, oracle_method=1):
    """
    Find what the correct decision should be ibs2 is the database we are working
    with ibs1 has pristine groundtruth
    """
    print('Oracle is making decision')
    if metatup is None:
        return None

    def oracle_method1(ibs1, ibs2, qnid1, aid_list2, aid2_to_aid1):
        """ METHOD 1: MAKE BEST DECISION FROM GIVEN INFORMATION """
        # Map annotations to ibs1 annotation rowids
        aid_list1 = ut.dict_take_list(aid2_to_aid1, aid_list2)
        nid_list1 = ibs1.get_annot_name_rowids(aid_list1)
        # Using ibs1 nameids find the correct index in returned results
        correct_index = ut.listfind(nid_list1, qnid1)
        if correct_index is None:
            # If the correct result was not presented create a new name
            name2 = None
        else:
            # Otherwise return the correct result
            nid2 = sorted_nids[correct_index]
            name2 = ibs2.get_name_texts(nid2)
        return name2

    def oracle_method2(ibs1, qnid1):
        """ METHOD 2: MAKE THE ABSOLUTE CORRECT DECISION REGARDLESS OF RESULT """
        name2 = ibs1.get_name_texts(qnid1)
        return name2

    #ut.embed()
    # Get the annotations that the user can see
    aid_list2 = ut.get_list_column(sorted_aids, 0)
    # Get name rowids of the query from ibs1
    (ibs1, ibs2, aid1_to_aid2) = metatup
    aid2_to_aid1 = ut.invert_dict(aid1_to_aid2)
    qannot_rowid1 = aid2_to_aid1[qaid]
    qnid1 = ibs1.get_annot_name_rowids(qannot_rowid1)
    # Make an oracle decision by choosing a name (like a user would)
    if oracle_method == 1:
        print('Oracle is using method 1')
        name2 = oracle_method1(ibs1, ibs2, qnid1, aid_list2, aid2_to_aid1)
    elif oracle_method == 2:
        print('Oracle is using method 2')
        name2 = oracle_method2(ibs1, qnid1)
    else:
        raise AssertionError('unknown oracle method %r' % (oracle_method,))
    print('Oracle decision is name2=%r' % (name2,))
    return name2


@ut.indent_func
def query_vsone_verified(ibs, qaids, daids):
    """
    A hacked in vsone-reranked pipeline
    Actually just two calls to the pipeline
    """
    from ibeis import ibsfuncs  # NOQA

    if len(daids) == 0:
        return {qaid: None for qaid in qaids}, None

    print('issuing vsmany part')

    def choose_vsmany_K(ibs, qaids, daids):
        K = ibs.cfg.query_cfg.nn_cfg.K
        if len(daids) < 10:
            K = 1
        if len(ut.intersect_ordered(qaids, daids)) > 0:
            # if self is in query bump k
            K += 1
        return K

    #interactive = False
    cfgdict = {
        #'pipeline_root': 'vsmany',
        'K': choose_vsmany_K(ibs, qaids, daids),
        'index_method': 'multi',
    }

    use_cache = False

    qaid2_qres_vsmany, qreq_ = ibs._query_chips4(qaids, daids, cfgdict=cfgdict,
                                                 return_request=True,
                                                 use_cache=use_cache)
    #qaid2_qres, qreq_ = ibs._query_chips4(sample_aids, [], return_request=True)

    print('finished vsmany part')

    isnsum = qreq_.qparams.score_method == 'nsum'
    assert isnsum
    assert qreq_.qparams.pipeline_root != 'vsone'
    #qreq_.qparams.prescore_method

    # build vs one list
    print('[query_vsone_verified] building vsone pairs')
    vsone_query_pairs = []
    nShortlistVsone = 5
    for qaid, qres in six.iteritems(qaid2_qres_vsmany):
        sorted_nids, sorted_nscores = qres.get_sorted_nids_and_scores(ibs=ibs)
        nShortlistVsone_ = min(len(sorted_nids), nShortlistVsone)
        top_nids = sorted_nids[0:nShortlistVsone_]
        # get top annotations beloning to the database query
        # TODO: allow annots not in daids to be included
        flat_top_nids = ut.flatten(ibs.get_name_aids(top_nids))
        top_aids = ut.intersect_ordered(flat_top_nids, qres.daids)
        vsone_query_pairs.append((qaid, top_aids))

    print('built %d pairs' % (len(vsone_query_pairs),))

    # vs-one reranking
    qaid2_qres_vsone = {}
    for qaid, top_aids in vsone_query_pairs:
        vsone_cfgdict = dict(codename='vsone_norm')
        qaid2_qres_vsone_, qreq_ = ibs._query_chips4([qaid], top_aids,
                                                     cfgdict=vsone_cfgdict,
                                                     return_request=True,
                                                     use_cache=use_cache)
        qres = qaid2_qres_vsone_[qaid]
        qaid2_qres_vsone[qaid] = qres
        #ut.embed()

    print('finished vsone queries')

    for qaid in qaids:
        qres_vsone = qaid2_qres_vsone[qaid]
        qres_vsmany = qaid2_qres_vsmany[qaid]
        if qres_vsmany is not None:
            vsmanyinspectstr = qres_vsmany.get_inspect_str(ibs=ibs, name_scoring=True)
            print(ut.msgblock(
                'VSMANY-INITIAL-RESULT qaid=%r' % (qaid,),
                vsmanyinspectstr))
        if qres_vsone is not None:
            vsoneinspectstr = qres_vsone.get_inspect_str(ibs=ibs, name_scoring=True)
            print(ut.msgblock(
                'VSONE-VERIFIED-RESULT qaid=%r' % (qaid,),
                vsoneinspectstr))

    # FIXME: returns the last qreq_. There should be a notion of a query
    # request for a vsone reranked query
    qaid2_qres = qaid2_qres_vsone
    return qaid2_qres, qreq_


def test_vsone_verified(ibs):
    """
    hack in vsone-reranking

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.all_imports import *  # NOQA
        >>> #reload_all()
        >>> from ibeis.model.hots.automated_matcher import *  # NOQA
        >>> import ibeis
        >>> ibs = ibeis.opendb('PZ_MTEST')
        >>> test_vsone_verified(ibs)
    """
    import plottool as pt
    #qaids = ibs.get_easy_annot_rowids()
    nids = ibs.get_valid_nids(filter_empty=True)
    grouped_aids_ = ibs.get_name_aids(nids)
    grouped_aids = list(filter(lambda x: len(x) > 1, grouped_aids_))
    items_list = grouped_aids

    sample_aids = ut.flatten(ut.sample_lists(items_list, num=2, seed=0))
    qaid2_qres, qreq_ = query_vsone_verified(ibs, sample_aids, sample_aids)
    for qres in ut.InteractiveIter(list(six.itervalues(qaid2_qres))):
        pt.close_all_figures()
        fig = qres.ishow_top(ibs)
        fig.show()
    #return qaid2_qres


if __name__ == '__main__':
    """
    CommandLine:
        python -m ibeis.model.hots.automated_helpers
        python -m ibeis.model.hots.automated_helpers --allexamples
        python -m ibeis.model.hots.automated_helpers --allexamples --noface --nosrc
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()