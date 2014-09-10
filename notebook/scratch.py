import ibeis
import six
import vtool
import utool
import numpy as np
import numpy.linalg as npl  # NOQA
import pandas as pd
from vtool import clustering2 as clustertool
from vtool import nearest_neighbors as nntool
from plottool import draw_func2 as df2
np.set_printoptions(precision=2)
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', 10)
pd.set_option('isplay.notebook_repr_html', True)
ibeis.ensure_pz_mtest()

#taids = ibs.get_valid_aids()
#tvecs_list = ibs.get_annot_desc(taids)
#tkpts_list = ibs.get_annot_kpts(taids)
#tvec_list = np.vstack(tvecs_list)
#print(idx2_vec)

#labels, words = vtool.clustering.cached_akmeans(tvec_list, 1000, 30, cache_dir='.')
#tvecdf_list = [pd.DataFrame(vecs) for vecs in  tvecs_list]
#tvecs_df = pd.DataFrame(tvecdf_list, index=taids)
#kpts_col = pd.DataFrame(tkpts_list, index=taids, columns=['kpts'])
#vecs_col = pd.DataFrame(tvecs_list, index=taids, columns=['vecs'])
#tvecs_dflist = [pd.DataFrame(vecs, index=np.arange(len(vecs))) for vecs in tvecs_list]
#pd.concat(tvecs_dflist)
## Bui


#taids = ibs.get_valid_aids()
#tvecs_list = ibs.get_annot_desc(taids)
#tkpts_list = ibs.get_annot_kpts(taids)

#orig_idx2_vec, orig_idx2_ax, orig_idx2_fx = vtool.nearest_neighbors.invertable_stack(tvecs_list, taids)
#annots_df = pd.concat([vecs_col, kpts_col], axis=1)
#annots_df

#idx2_vec = np.vstack(annots_df['vecs'].values)
##idx2_ax =
#idx2_vec, idx2_ax, idx2_fx = vtool.nearest_neighbors.invertable_stack(tvecs_list, taids)


#labels, words = vtool.clustering2.cached_akmeans(tvec_list, 1000, 30)
#words = centroids


def display_info(ibs, invindex, annots_df):
    #################
    #from ibeis.dev import dbinfo
    #print(ibs.get_infostr())
    #dbinfo.get_dbinfo(ibs, verbose=True)
    #################
    #print('Inverted Index Stats: vectors per word')
    #print(utool.stats_str(map(len, invindex.wx2_idxs.values())))
    #################
    qfx2_vec     = annots_df['vecs'][1]
    centroids    = invindex.words
    num_pca_dims = 3  # 3
    whiten       = False
    kwd = dict(num_pca_dims=num_pca_dims,
               whiten=whiten,)
    #clustertool.rrr()
    def makeplot_(fnum, prefix, data, labels='centroids', centroids=centroids):
        return clustertool.plot_centroids(data, centroids, labels=labels,
                                          fnum=fnum, prefix=prefix + '\n', **kwd)
    #makeplot_(1, 'centroid vecs', centroids)
    #makeplot_(2, 'database vecs', invindex.idx2_vec)
    #makeplot_(3, 'query vecs', qfx2_vec)
    #makeplot_(4, 'database vecs', invindex.idx2_vec)
    #makeplot_(5, 'query vecs', qfx2_vec)
    #################

def make_annot_df(ibs):
    aid_list = ibs.get_valid_aids()
    _kpts_col = pd.DataFrame(ibs.get_annot_kpts(aid_list),
                             index=aid_list, columns=['kpts'])
    _vecs_col = pd.DataFrame(ibs.get_annot_desc(aid_list),
                             index=aid_list, columns=['vecs'])
    annots_df = pd.concat([_vecs_col, _kpts_col], axis=1)
    return annots_df


def learn_visual_words(annots_df, train_aids, nCentroids):
    vecs_list = annots_df['vecs'][train_aids].as_matrix()
    train_vecs = np.vstack(vecs_list)
    print('Training %d word vocabulary with %d annots and %d descriptors' %
          (nCentroids, len(train_aids), len(train_vecs)))
    words = clustertool.cached_akmeans(train_vecs, nCentroids, max_iters=100)
    return words


def index_data_annots(annots_df, daids, words):
    vecs_list = annots_df['vecs'][daids]
    flann_params = {}
    wordflann = vtool.nearest_neighbors.flann_cache(words, flann_params=flann_params)
    ax2_aid = np.array(daids)
    idx2_vec, idx2_ax, idx2_fx = nntool.invertable_stack(vecs_list, np.arange(len(ax2_aid)))
    invindex = InvertedIndex(words, wordflann, idx2_vec, idx2_ax, idx2_fx, ax2_aid)
    invindex.compute_internals()
    return invindex


@six.add_metaclass(utool.ReloadingMetaclass)
class InvertedIndex(object):
    def __init__(invindex, words, wordflann, idx2_vec, idx2_ax, idx2_fx, ax2_aid):
        invindex.wordflann = wordflann
        invindex.words     = words     # visual word centroids
        invindex.ax2_aid   = ax2_aid   # annot index -> annot id
        invindex.idx2_vec  = idx2_vec  # stacked index -> descriptor vector
        invindex.idx2_ax   = idx2_ax   # stacked index -> annot index
        invindex.idx2_fx   = idx2_fx   # stacked index -> feature index
        invindex.idx2_wx  = None       # stacked index -> word index
        invindex.wx2_idxs = None       # word index -> stacked indexes
        invindex.wx2_drvecs = None     # word index -> residual vectors
        #invindex.compute_internals()

    def compute_internals(invindex):
        idx2_vec = invindex.idx2_vec
        wx2_idxs, idx2_wx = invindex.inverted_assignments(idx2_vec)
        wx2_drvecs = invindex.compute_residuals(idx2_vec, wx2_idxs)
        invindex.idx2_wx = idx2_wx
        invindex.wx2_idxs = wx2_idxs
        invindex.wx2_drvecs = wx2_drvecs

    def inverted_assignments(invindex, idx2_vec):
        idx2_wx, _idx2_wdist = invindex.wordflann.nn_index(idx2_vec, 1)
        if True:
            assign_df = pd.DataFrame(idx2_wx, columns=['wordindex'])
            grouping = assign_df.groupby('wordindex')
            wx2_idxs = grouping.wordindex.indices
        else:
            # TODO: replace with pandas groupby
            idx_list = list(range(len(idx2_wx)))
            wx2_idxs = utool.group_items(idx_list, idx2_wx.tolist())
        return wx2_idxs, idx2_wx

    def compute_residuals(invindex, idx2_vec, wx2_idxs):
        """ returns mapping from word index to a set of residual vectors """
        words = invindex.words
        wx2_rvecs = {}
        for word_index in wx2_idxs.keys():
            # for each word
            idxs = wx2_idxs[word_index]
            vecs = np.array(idx2_vec[idxs], dtype=np.float64)
            word = np.array(words[word_index], dtype=np.float64)
            # compute residuals of all vecs assigned to this word
            residuals = np.array([word - vec for vec in vecs])
            # normalize residuals
            residuals_n = vtool.linalg.normalize_rows(residuals)
            wx2_rvecs[word_index] = residuals_n
        return wx2_rvecs


#def smk_similarity(wx2_qrvecs, wx2_drvecs):
#    similarity_matrix = (rvecs1.dot(rvecs2.T))


def query_inverted_index(annots_df, qaid, invindex):
    qfx2_vec = annots_df['vecs'][qaid]
    wx2_qfxs, qfx2_wx = invindex.inverted_assignments(qfx2_vec)
    wx2_qrvecs = invindex.compute_residuals(qfx2_vec, wx2_qfxs)

    daid = invindex.ax2_aid[0]

    def selectivity_function(rscore_mat, alpha=3, thresh=0):
        """ sigma from SMK paper rscore = residual score """
        scores = (np.sign(rscore_mat) * np.abs(rscore_mat)) ** alpha
        scores[scores <= thresh] = 0
        return scores

    # Entire database
    daid2_score = utool.ddict(lambda: 0)
    query_wxs = set(wx2_qrvecs.keys())
    data_wxs  = set(invindex.wx2_drvecs.keys())
    qfx2_axs = []
    qfx2_fm = []
    qfx2_fs = []
    aid_fm = []
    aid_fs = []

    idx2_daid = pd.Series(invindex.ax2_aid[invindex.idx2_ax], name='daid')
    idx2_dfx  = pd.Series(invindex.idx2_fx, name='dfx')
    idx2_wfx  = pd.Series(invindex.idx2_wx, name='dwx')
    invindex.idx_df = pd.concat((idx2_daid, idx2_dfx, idx2_wfx), axis=1, names=['idx'])

    wx2_idxs = {wx: pd.Series(idxs, name='idx') for wx, idxs in six.iteritems(invindex.wx2_idxs)}
    wx2_qfxs = {wx: pd.Series(qfx, name='qfx') for wx, qfx in six.iteritems(wx2_qfxs)}

    for wx in data_wxs.intersection(query_wxs):
        # all pairs of scores
        _idxs = wx2_idxs[wx]
        qfxs = wx2_qfxs[wx]
        qfx2_idx = np.tile(_idxs, (len(qfxs), 1))
        qfx2_aid = np.tile(invindex.idx_df['daid'].take(_idxs), (len(qfxs), 1))
        qfx2_fx = np.tile(invindex.idx_df['dfx'].take(_idxs), (len(qfxs), 1))
        qrvecs = wx2_qrvecs[wx]
        drvecs = invindex.wx2_drvecs[wx]
        qfx2_wordscore_ = selectivity_function(qrvecs.dot(drvecs.T))
        qfx2_wordscore = pd.DataFrame(qfx2_wordscore_, index=qfxs, columns=_idxs)
        qfx2_datascore = qfx2_wordscore.groupby(invindex.idx_df['daid'], axis=1).sum()
        daid2_wordscore = qfx2_datascore.sum(axis=0)
        for aid in daid2_wordscore.index:
            daid2_score[aid] = daid2_wordscore[aid]
        #score_mi = pd.MultiIndex.from_product((qfxs, _idxs), names=('qfxs', '_idxs'))
        #print()
        #score_df = pd.DataFrame(score_matrix, index=score_mi)
        # Scores for each database vector
        #scores = pd.DataFrame(score_matrix.sum(axis=0), columns=['score'])
        # Use cartesian product of these indexes to produce feature matches
        #qfxs = pd.DataFrame(wx2_qfxs[wx], columns=['qfx'])
        #dfxs = pd.DataFrame(invindex.idx2_fx[_idxs], columns=['dfx'])
        #daxs = pd.DataFrame(invindex.idx2_ax[_idxs], columns=['dax'])
        #daids = pd.DataFrame(invindex.ax2_aid[invindex.idx2_ax[_idxs]], columns=['daid'])
        #print(scores)
        #print(daids)
        #result_df = pd.concat((scores, daids), axis=1)  # concat columns
        #daid_group = result_df.groupby(['daid'])
        #daid2_wordscore = daid_group['score'].sum()
    print(utool.dict_str(daid2_score))
    aidkeys = np.array(daid2_score.keys())
    totalscores = np.array(daid2_score.values())
    sortx = totalscores.argsort()[::-1]
    ranked_aids = aidkeys[sortx]
    ranked_scores = totalscores[sortx]
    score_df = pd.DataFrame(ranked_scores, index=ranked_aids, columns=['score'])
    print(score_df)
    return wx2_qrvecs


def main():
    ibs = ibeis.opendb('PZ_MTEST')
    # Pandas Annotation Dataframe
    annots_df = make_annot_df(ibs)
    valid_aids = annots_df.index
    # Training set
    train_aids = valid_aids[0:20:2]
    # Database set
    daids  = valid_aids[3:30:2]
    # Search set
    #qaids = valid_aids[0::2]
    qaids = valid_aids[0:1]
    qaid = qaids[0]
    nCentroids = K = 10
    words = learn_visual_words(annots_df, train_aids, nCentroids)
    invindex = index_data_annots(annots_df, daids, words)
    wx2_drvecs = invindex.wx2_drvecs
    wx2_qrvecs = query_inverted_index(annots_df, qaid, invindex)
    display_info(ibs, invindex, annots_df)
    return locals()


if __name__ == '__main__':
    main_locals = main()
    main_execstr = utool.execstr_dict(main_locals, 'main_locals')
    exec(main_execstr)
    exec(df2.present())
