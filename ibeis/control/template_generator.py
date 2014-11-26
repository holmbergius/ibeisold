"""
Templated Autogenerator for the IBEIS Controller

Concepts:

    template definitions are in template_def.py

    ALL_CAPS_VARIABLES: stores the name of a python GLOBAL constant
        EG:
            * COLNAME : stores the name of a python constant like 'FEAT_ROWID'
            * MULTICOLNAME : stores the name of a python constant that contains the actual

    all_lower_variables: stores the template python representation.
         EG:
             * colname: stores the actual column name like 'feature_rowid'

CommandLine:
    python ibeis/control/template_generator.py
    python ibeis/control/template_generator.py --dump-autogen-controller

TODO:
   * autogen testdata function
   * finish autogen chips and features
   * add autogen probchip
   * consistency check that all chips in the sql table exist

"""
from __future__ import absolute_import, division, print_function
import six
import utool  # NOQA
import utool as ut
from ibeis import constants
from os.path import dirname, join, relpath  # NOQA
import ibeis.control.template_definitions as Tdef


STRIP_DOCSTR   = False
STRIP_LONGDESC = False  # True
STRIP_EXAMPLE  = False  # True
STRIP_COMMENTS = False
USE_SHORTNAMES = True
USE_FUNCTYPE_HEADERS = False  # True


REMOVE_NPARAMS = True
REMOVE_EAGER = True
REMOVE_QREQ = False
WITH_PEP8 = True
WITH_DECOR = True


#STRIP_DOCSTR   = True
#STRIP_COMMENTS  = True

constants.PROBCHIP_TABLE = 'probchips'

TBLNAME_LIST = [
    #constants.ANNOTATION_TABLE,
    #constants.CHIP_TABLE,
    #constants.PROBCHIP_TABLE,
    #constants.FEATURE_TABLE,
    constants.FEATURE_WEIGHT_TABLE,
    #constants.RESIDUAL_TABLE
]

multicolumns_dict = ut.odict([
    (constants.CHIP_TABLE, [
        ('annot_size', ('chip_width', 'chip_height')),
    ]),
    (constants.ANNOTATION_TABLE, [
        ('annot_bbox', ('annot_xtl', 'annot_ytl', 'annot_width', 'annot_height')),
        ('annot_visualinfo', ('annot_verts', 'annot_theta', 'annot_view')),
        # TODO: Need to make this happen by performing nested sql calls
        #('annot_semanticinfo', ('annot_image_uuid', 'annot_verts', 'annot_theta', 'annot_view', 'annot_name', 'annot_species')),
    ]),
])

readonly_set = {
    constants.CHIP_TABLE,
    #constants.PROBCHIP_TABLE,
    #constants.FEATURE_TABLE,
    #constants.FEATURE_WEIGHT_TABLE,
    #constants.RESIDUAL_TABLE
}


# HACK
class SHORTNAMES(object):
    ANNOT      = 'annot'
    CHIP       = 'chip'
    PROBCHIP   = 'probchip'
    FEAT       = 'feat'
    FEATWEIGHT = 'featweight'
    RVEC       = 'residual'  # 'rvec'
    VOCABTRAIN = 'vocabtrain'
    DETECT     = 'detect'

depends_map = {
    SHORTNAMES.ANNOT: None,
    SHORTNAMES.CHIP:       SHORTNAMES.ANNOT,
    SHORTNAMES.PROBCHIP:   SHORTNAMES.CHIP,
    SHORTNAMES.FEAT:       SHORTNAMES.CHIP,
    SHORTNAMES.FEATWEIGHT: SHORTNAMES.FEAT,  # TODO: and PROBCHIP
    SHORTNAMES.RVEC:       SHORTNAMES.FEAT,
}

# shortened tablenames
tablename2_tbl = {
    constants.ANNOTATION_TABLE     : SHORTNAMES.ANNOT,
    constants.CHIP_TABLE           : SHORTNAMES.CHIP,
    constants.PROBCHIP_TABLE       : SHORTNAMES.PROBCHIP,
    constants.FEATURE_TABLE        : SHORTNAMES.FEAT,
    constants.FEATURE_WEIGHT_TABLE : SHORTNAMES.FEATWEIGHT,
    constants.RESIDUAL_TABLE       : SHORTNAMES.RVEC,
}


# FIXME: keys might conflict and need to be ordered
variable_aliases = {
    #'chip_rowid_list': 'cid_list',
    #'annot_rowid_list': 'aid_list',
    #'feature_rowid_list': 'fid_list',
    #

    #'chip_rowid'                  : 'cid',
    'annot_rowid'                 : 'aid',
    #'feat_rowid'                  : 'fid',
    'num_feats'                   : 'nFeat',
    'featweight_forground_weight' : 'fgweight',
    'keypoints'                   : 'kpt_arr',
    'vecs'                        : 'vec_arr',
    'residualvecs'                : 'rvec_arr',
    'verts'                       : 'vert_arr',
}


func_aliases = {
    #'get_feat_vec_lists': 'get_feat_vecs',
    #'get_feat_kpt_lists': 'get_feat_kpts',
}

# mapping to variable names in constants
tbl2_tablename = ut.invert_dict(tablename2_tbl)
tbl2_TABLE = {key: ut.get_varname_from_locals(val, constants.__dict__)
              for key, val in six.iteritems(tbl2_tablename)}

# Lets just use strings in autogened files for now: TODO: use constant vars
# later
#tbl2_TABLE = {key: '\'%s\'' % (val,) for key, val in six.iteritems(tbl2_tablename)}
tbl2_TABLE = {key: 'constants.' + ut.get_varname_from_locals(val, constants.__dict__)
                for key, val in six.iteritems(tbl2_tablename)}


def remove_sentinals(code_text):
    """ Removes template comments and vim sentinals """
    code_text = ut.regex_replace(r'^ *# STARTBLOCK *$\n', '', code_text)
    code_text = ut.regex_replace(r'^ *# ENDBLOCK *$\n?', '', code_text)
    code_text = ut.regex_replace(r'^ *# *REM [^\n]*$\n?', '', code_text)
    code_text = code_text.rstrip()
    return code_text


def format_controller_func(func_code, flagskw):
    """
    Applys formatting and filtering to function code strings

    CommandLine:
        python ibeis/control/template_generator.py
    """
    func_code = remove_sentinals(func_code)
    # BOTH OPTIONS ARE NOT GARUENTEED TO WORK. If there are bugs here may be a
    # good place to look.
    if REMOVE_NPARAMS:
        func_code = remove_kwarg('nInput', 'None', func_code)
    if REMOVE_EAGER:
        func_code = remove_kwarg('eager', 'True', func_code)
    if REMOVE_QREQ:
        func_code = remove_kwarg('qreq_', 'None', func_code)
        func_code = func_code.replace('if qreq_ is not None', 'if False')
    if STRIP_COMMENTS:
        func_code = ut.strip_line_comments(func_code)
    if flagskw.get('strip_docstr', STRIP_DOCSTR):
        # HACKY: might not always work. newline HACK away dumb blank line
        func_code = ut.regex_replace('""".*"""\n    ', '', func_code)
    else:
        if STRIP_LONGDESC:
            func_code_lines = func_code.split('\n')
            new_lines = []
            begin = False
            startstrip = False
            finished = False
            for line in func_code_lines:
                if finished is False:
                    # Find the start of the docstr
                    striped_line = line.strip()
                    if not begin and striped_line.startswith('"""') or striped_line.startswith('r"""'):
                        begin = True
                    elif begin:
                        # A blank line signals the start and end of the long
                        # description
                        if len(striped_line) == 0 or striped_line.startswith('"""'):
                            if startstrip is False:
                                # Found first blank line, start stripping
                                startstrip = True
                            else:
                                finished = True
                                #continue
                        elif startstrip:
                            continue
                new_lines.append(line)
            func_code = '\n'.join(new_lines)
        if STRIP_EXAMPLE:
            func_code = ut.regex_replace('Example.*"""', '"""', func_code)
    if USE_SHORTNAMES:
        # Execute search and replaces without changing strings
        func_code = ut.replace_nonquoted_text(func_code,
                                              variable_aliases.keys(),
                                              variable_aliases.values())
    # add decorators
    if flagskw.get('with_decor', WITH_DECOR):
        func_code = '@register_ibs_method\n' + func_code
    # ensure pep8 formating
    if flagskw.get('with_pep8', WITH_PEP8):
        func_code = ut.autofix_codeblock(func_code).strip()
    return func_code


def get_tableinfo(tablename, ibs=None):
    """
    Gets relevant info from the sql controller and dependency graph
    """
    dbself = None
    tableinfo = None
    if ibs is not None:
        valid_db_tablenames = ibs.db.get_table_names()
        valid_dbcache_tablenames = ibs.dbcache.get_table_names()

        sqldb = None
        if tablename in valid_db_tablenames:
            sqldb = ibs.db
            dbself = 'db'
        elif tablename in valid_dbcache_tablenames:
            if sqldb is not None:
                raise AssertionError('Tablename=%r is specified in both schemas' % tablename)
            sqldb = ibs.dbcache
            dbself = 'dbcache'
        else:
            print('WARNING unknown tablename=%r' % tablename)

        if sqldb is not None:
            all_colnames = sqldb.get_column_names(tablename)
            superkey_colnames = sqldb.get_table_superkey_colnames(tablename)
            primarykey_colnames = sqldb.get_table_primarykey_colnames(tablename)
            other_colnames = sqldb.get_table_otherkey_colnames(tablename)
    if dbself is None:
        dbself = 'dbunknown'
        all_colnames        = []
        superkey_colnames   = []
        primarykey_colnames = []
        other_colnames      = []
        if tablename == constants.FEATURE_WEIGHT_TABLE:
            dbself = 'dbcache'
            all_colnames = ['feature_weight_fg']
    if tablename == constants.RESIDUAL_TABLE:
        other_colnames.append('rvecs')
    tableinfo = (dbself, all_colnames, superkey_colnames, primarykey_colnames, other_colnames)
    return tableinfo


def remove_kwarg(kwname, kwdefault, func_code):
    func_code = ut.regex_replace(r' *>>> *{0} *= *{1} *\n'.format(kwname, kwdefault), '', func_code)
    func_code = ut.regex_replace(r',? *{0} *= *{1}'.format(kwname, kwname), '', func_code)
    for val in kwdefault if isinstance(kwdefault, (list, tuple)) else [kwdefault]:
        func_code = ut.regex_replace(r',? *{0} *= *{1}'.format(kwname, val), '', func_code)
    return func_code


def parse_first_func_name(func_code):
    try:
        parse_result = ut.padded_parse('def {func_name}({args}):', func_code)
        assert parse_result is not None
        func_name = parse_result['func_name']
    except AssertionError as ex:
        ut.printex(ex, 'parse result is None', keys=['parse_result', 'func_code'])
        raise
    return func_name


def build_depends_path(child):
    parent = depends_map[child]
    if parent is not None:
        return build_depends_path(parent) + [child]
    else:
        return [child]
    #depends_list = ['annot', 'chip', 'feat', 'featweight']


def postprocess_and_combine_templates(autogen_rel_fpath, constant_list_, tblname2_functype2_func_list, flagskw):
    """ Sorts and combines augen function dictionary """
    func_name_list = []
    func_type_list = []
    func_code_list = []
    func_tbl_list = []

    #functype_set = set([])
    for tblname, functype2_funclist in six.iteritems(tblname2_functype2_func_list):
        for functype, funclist in six.iteritems(functype2_funclist):
            for func_tup in funclist:
                func_name, func_code = func_tup
                # Append code to flat lists
                func_tbl_list.append(tblname)
                func_type_list.append(functype)
                func_name_list.append(func_name)
                func_code_list.append(func_code)

    # sort by multiple values
    #sorted_indexes = ut.list_argsort(func_tbl_list, func_name_list, func_type_list)
    sorted_indexes = ut.list_argsort(func_name_list, func_tbl_list, func_type_list)
    sorted_func_code = ut.list_take(func_code_list, sorted_indexes)
    #sorted_func_name = ut.list_take(func_name_list, sorted_indexes)
    #sorted_func_type = ut.list_take(func_type_list, sorted_indexes)
    #sorted_func_tbl = ut.list_take(func_tbl_list, sorted_indexes)

    #functype_set.add(functype)
    #functype_list = sorted(list(functype_set))

    body_codeblocks = []
    for func_code in sorted_func_code:
        body_codeblocks.append(func_code)

    # --- MORE POSTPROCESSING ---

    # Append constants to body
    aligned_constants = '\n'.join(ut.align_lines(sorted(list(set(constant_list_)))))
    autogen_constants = ('# AUTOGENED CONSTANTS:\n' + aligned_constants)
    autogen_constants += '\n\n'

    # Make main docstr
    #testable_name_list = ['get_annot_featweight_rowids']
    def make_docstr_main(autogen_rel_fpath):
        """ Creates main docstr """
        main_commandline_block_lines = [
            'python ' + autogen_rel_fpath,
        ]
        main_commandline_block_lines.append('python ' + autogen_rel_fpath + ' --allexamples')
        main_commandline_block = '\n'.join(main_commandline_block_lines)
        main_commandline_docstr = 'CommandLine:\n' + utool.indent(main_commandline_block, ' ' * 8)
        main_docstr_blocks = [main_commandline_docstr]
        main_docstr_body = '\n'.join(main_docstr_blocks)
        return main_docstr_body

    main_docstr_body = make_docstr_main(autogen_rel_fpath)

    # --- CONCAT ---
    # Contenate autogen parts into autogen_text

    if flagskw.get('with_header', True):
        autogen_header = remove_sentinals(Tdef.Theader_ibeiscontrol.format(timestamp=ut.get_timestamp('printable')))
        autogen_header += '\n\n'
    else:
        autogen_header = ''

    autogen_body = ('\n\n\n'.join(body_codeblocks)) + '\n'

    if flagskw.get('with_footer', True):
        autogen_footer = remove_sentinals(Tdef.Tfooter_ibeiscontrol.format(main_docstr_body=main_docstr_body))
        autogen_footer += '\n\n'
    else:
        autogen_footer = ''

    autogen_text = ''.join([
        autogen_header,
        autogen_constants,
        autogen_body,
        autogen_footer,
    ])

    # POSTPROCESSING HACKS:
    #autogen_text = autogen_text.replace('\'feat_rowid\'', '\'feature_rowid\'')
    #autogen_text = ut.regex_replace(r'kptss', 'kpt_lists', autogen_text)
    #autogen_text = ut.regex_replace(r'vecss', 'vec_lists', autogen_text)
    #autogen_text = ut.regex_replace(r'nFeatss', 'nFeat_list', autogen_text)
    #autogen_text = autogen_text.replace('\'feat_rowid\'', '\'feature_rowid\'')

    return autogen_text


def build_templated_funcs(ibs, autogen_modname, tblname_list, flagdefault=True, flagskw={}):
    """ Builds lists of requested functions"""
    #child = 'featweight'
    tblname2_functype2_func_list = ut.ddict(lambda: ut.ddict(list))
    # HACKED IN CONSTANTS
    constant_list_ = [
        'CONFIG_ROWID = \'config_rowid\'',
        'FEATWEIGHT_ROWID = \'featweight_rowid\'',
    ]
    # --- AUTOGENERATE FUNCTION TEXT ---
    for tablename in tblname_list:
        tableinfo = get_tableinfo(tablename, ibs)
        tup = build_controller_table_funcs(tablename, tableinfo,
                                           autogen_modname,
                                           flagdefault=flagdefault,
                                           flagskw=flagskw)
        functype2_func_list, constant_list = tup
        constant_list_.extend(constant_list)
        tblname2_functype2_func_list[tablename] = functype2_func_list
    return constant_list_, tblname2_functype2_func_list


def get_autogen_modpaths(autogen_mod_fname=None):
    """
    Returns info on where the autogen module will be placed if is written
    """
    # Build output filenames and info
    if autogen_mod_fname is None:
        autogen_mod_fname = '_autogen_ibeiscontrol_funcs.py'
    # module we will autogenerate next to
    parent_module = ibeis.control
    parent_modpath = dirname(parent_module.__file__)
    # Build autogen paths and modnames
    autogen_fpath = join(parent_modpath, autogen_mod_fname)
    autogen_rel_fpath = ut.get_relative_modpath(autogen_fpath)
    autogen_modname = ut.get_modname_from_modpath(autogen_fpath)
    return autogen_fpath, autogen_rel_fpath, autogen_modname


def build_controller_table_funcs(tablename, tableinfo, autogen_modname, flagdefault=True, flagskw={}):
    """
    BIG FREAKING FUNCTION THAT REALIZES TEMPLATES

    Builds function strings for a single type of table using the template
    definitions.

    Args:
        tablename (?):
        tableinfo (?):
        autogen_modname (?):
        flagdefault (?):
        flagskw : flag different types of functions to be enabled disabled

    Returns:
        tuple: (functype2_func_list, constant_list)

    CommandLine:
        python ibeis/control/template_generator.py
        python ibeis/control/template_generator.py --dump-autogen-controller
    """
    # +-----
    # Setup
    # +-----
    def colname2_col(colname, tablename):
        # col is a short alias for colname
        return colname
        #col = colname.replace(ut.singular_string(tablename) + '_', '')
        #return col

    (dbself, all_colnames, superkey_colnames, primarykey_colnames, other_colnames) = tableinfo
    other_cols = list(map(lambda colname: colname2_col(colname, tablename), other_colnames))
    other_COLNAMES = list(map(lambda colname: colname.upper(), other_colnames))
    nonprimary_leaf_colnames = ut.setdiff_ordered(all_colnames, primarykey_colnames)
    leaf_other_propnames = ', '.join(other_colnames)
    #leaf_other_propname_lists = ', '.join([colname + '_list' for colname in other_colnames])
    # for the preproc_tbe.compute... method
    leaf_props = '_'.join(other_colnames)
    superkey_args = ', '.join([colname + '_list' for colname in superkey_colnames])

    # WE WILL DEFINE SEVERAL CLOSURES THAT USE THIS DICTIONARY
    fmtdict = {
    }

    fmtdict['nonprimary_leaf_colnames'] = nonprimary_leaf_colnames
    fmtdict['autogen_modname'] = autogen_modname
    fmtdict['leaf_other_propnames'] = leaf_other_propnames
    #fmtdict['leaf_other_propname_lists'] = leaf_other_propname_lists
    fmtdict['leaf_props'] = leaf_props
    fmtdict['superkey_args'] = superkey_args
    fmtdict['self'] = 'ibs'
    fmtdict['dbself'] = dbself

    CONSTANT_COLNAMES = []
    CONSTANT_COLNAMES.extend(other_colnames)
    functype2_func_list = ut.ddict(list)
    constant_list = []
    # L_____

    # +----------------------------
    # | Format dict helper functions
    # +----------------------------
    def _setupper(fmtdict, key, val):
        fmtdict[key] = val
        fmtdict[key.upper()] = val.upper()

    def set_parent_child(parent, child):
        _setupper(fmtdict, 'parent', parent)
        _setupper(fmtdict, 'child', child)

    def set_root_leaf(root, leaf, leaf_parent):
        _setupper(fmtdict, 'root', root)
        _setupper(fmtdict, 'leaf', leaf)
        _setupper(fmtdict, 'leaf_parent', leaf_parent)
        fmtdict['LEAF_TABLE'] = tbl2_TABLE[leaf]  # tblname1_TABLE[child]
        fmtdict['ROOT_TABLE'] = tbl2_TABLE[root]  # tblname1_TABLE[child]

    def set_tbl(tbl):
        _setupper(fmtdict, 'tbl', tbl)
        fmtdict['TABLE'] = tbl2_TABLE[tbl]

    def set_col(col, COLNAME):
        fmtdict['COLNAME'] = COLNAME
        fmtdict['col'] = col

    def set_multicol(multicol, MULTICOLNAMES):
        fmtdict['MULTICOLNAMES'] = str(multicolnames)
        fmtdict['multicol'] = multicol
    # L____________________________

    # +----------------------------
    # | Template appenders
    # +----------------------------
    def append_constant(varname, valstr):
        """ Used for rowid and colname constants """
        const_fmtstr = ''.join((varname, ' = \'', valstr, '\''))
        const_line = const_fmtstr.format(**fmtdict)
        constant_list.append(const_line)

    def append_func(func_type, func_code_fmtstr, tablename=tablename):
        """
        Filters, formats, and organizes functions as they are added
        """
        #if func_type.find('add') < 0:
        #    return
        func_type = func_type
        try:
            func_code = func_code_fmtstr.format(**fmtdict)
            func_code = format_controller_func(func_code, flagskw)
            # HACK to remove double table names like: get_chip_chip_width
            single_tbl = fmtdict['tbl']
            double_tbl = single_tbl + '_' + single_tbl
            func_code = func_code.replace(double_tbl, single_tbl)
            # parse out function name
            func_name = parse_first_func_name(func_code)
            func_tup = (func_name, func_code)

            if func_name in func_aliases:
                func_aliasname = func_aliases[func_name]
                func_code += ut.codeblock('''
                @register_ibs_method
                def {func_aliasname}(*args, **kwargs):
                    return {func_name}(*args, **kwargs)
                ''').format(func_aliasname=func_aliasname, func_name=func_name)
            functype2_func_list[func_type].append(func_tup)
        except Exception as ex:
            utool.printex(ex, keys=['func_type', 'tablename'])
            raise
    # L____________________________

    # +----------------------------
    # | Higher level helper functions
    # +----------------------------
    def build_rowid_constants(depends_list):
        """ Ensures all rowid constants have been added corectly """
        for tbl_ in depends_list:
            set_tbl(tbl_)
            # HACK: fix feature column names in dbschema
            constval_fmtstr = '{tbl}_rowid' if tbl_ != 'feat' else 'feature_rowid'
            append_constant('{TBL}_ROWID', constval_fmtstr)

    def build_pc_dependant_lines(depends_list):
        """
        builds parent child dependency function chains for pc_line dependent
        templates
        """
        # Build pc dependeant lines
        pc_dependant_rowid_lines = []
        pc_dependant_delete_lines = []
        # For each parent child dependancy
        for parent, child in ut.itertwo(depends_list):
            set_parent_child(parent, child)
            # depenant rowid lines
            pc_dependant_rowid_lines.append( Tdef.Tline_pc_dependant_rowid.format(**fmtdict))
            pc_dependant_delete_lines.append(Tdef.Tline_pc_dependant_delete.format(**fmtdict))
        # At this point parent = leaf_parent and child=leaf
        fmtdict['pc_dependant_rowid_lines']  = ut.indent(ut.indentjoin(pc_dependant_rowid_lines)).strip()
        fmtdict['pc_dependant_delete_lines'] = ut.indent(ut.indentjoin(pc_dependant_delete_lines)).strip()
    # L____________________________

    tbl = tablename2_tbl[tablename]
    # Build dependency path
    depends_list = build_depends_path(tbl)

    #=========================================
    # THIS IS WHERE THE TEMPLATES ARE FORMATED
    #=========================================
    with_getters      = flagskw.get('with_getters', flagdefault)
    with_setters      = flagskw.get('with_setters', flagdefault)
    with_iders        = flagskw.get('with_iders', flagdefault)
    with_adders       = flagskw.get('with_adders', flagdefault)
    with_deleters     = flagskw.get('with_deleters', flagdefault)
    with_fromsuperkey = flagskw.get('with_fromsuperkey', flagdefault)
    with_configs      = flagskw.get('with_configs', flagdefault)

    with_columns      = flagskw.get('with_columns', True)
    with_multicolumns = flagskw.get('with_multicolumns', True)
    with_parentleaf   = flagskw.get('with_parentleaf', True)
    with_rootleaf     = flagskw.get('with_rootleaf', True)
    with_native       = flagskw.get('with_native', True)

    # Setup
    build_rowid_constants(depends_list)
    set_tbl(tbl)
    build_pc_dependant_lines(depends_list)

    # -----------------------
    #  Parent Leaf Dependency
    # -----------------------
    if len(depends_list) > 1 and with_parentleaf:
        if len(depends_list) == 2:
            set_root_leaf(depends_list[0], depends_list[-1], depends_list[0])
        else:
            set_root_leaf(depends_list[0], depends_list[-1], depends_list[-2])
        if with_adders:
            append_func('0_PL.adder',   Tdef.Tadder_pl_dependant)
        if with_getters:
            append_func('0_PL.getter_rowids_',  Tdef.Tgetter_pl_dependant_rowids_)
            append_func('0_PL.getter_rowids',   Tdef.Tgetter_pl_dependant_rowids)

    # ----------------------------
    # Root Leaf Dependancy
    # ----------------------------
    if len(depends_list) > 2 and with_rootleaf:
        set_root_leaf(depends_list[0], depends_list[-1], depends_list[-2])
        if with_adders:
            append_func('1_RL.adder',   Tdef.Tadder_rl_dependant)
        if with_deleters:
            append_func('1_RL.deleter', Tdef.Tdeleter_rl_depenant)
        if with_iders:
            append_func('1_RL.ider',    Tdef.Tider_rl_dependant_all_rowids)
        if with_getters:
            append_func('1_RL.getter_rowids',  Tdef.Tgetter_rl_dependant_rowids)

    # ------------------
    #  Native Noncolumn
    # ------------------
    if with_native:
        if with_deleters:
            append_func('2_Native.deleter', Tdef.Tdeleter_native_tbl)
        if with_iders:
            append_func('2_Native.ider', Tdef.Tider_all_rowids)
        if with_fromsuperkey:
            append_func('2_Native.fromsuperkey_getter', Tdef.Tgetter_native_rowid_from_superkey)
        # Only dependants have native configs
        if len(depends_list) > 1 and with_configs:
            append_func('2_Native.config_getter', Tdef.Tcfg_rowid_getter)

    # ------------------
    #  Column Properties
    # ------------------

    with_col_rootleaf = len(depends_list) > 1 and with_rootleaf

    if with_columns:
        # For each column property
        for colname, col, COLNAME in zip(other_colnames, other_cols, other_COLNAMES):
            set_col(col, COLNAME)
            if with_getters:
                # Getter template: columns
                if with_col_rootleaf:
                    append_func('1_RL.getter_col', Tdef.Tgetter_rl_pclines_dependant_column)
                if with_native:
                    append_func('2_Native.getter_col', Tdef.Tgetter_table_column)
            if with_setters and  tablename not in readonly_set:
                # Setter template: columns
                if with_native:
                    append_func('2_Native.setter', Tdef.Tsetter_native_column)
            constant_list.append(COLNAME + ' = \'%s\'' % (colname,))
            append_constant(COLNAME, colname)

    if with_multicolumns:
        # For each multicolumn property
        if tablename in multicolumns_dict:
            for multicol, multicolnames in multicolumns_dict[tablename]:
                set_multicol(multicol, multicolnames)
                if with_getters:
                    # Getter template: multicolumns
                    if with_col_rootleaf:
                        append_func('RL.Tgetter_mutli_dependant', Tdef.Tgetter_rl_pclines_dependant_multicolumn)
                    if with_native:
                        append_func('2_Native.Tgetter_multi_native', Tdef.Tgetter_native_multicolumn)
                pass

    return functype2_func_list, constant_list


def get_autogen_text(
        tblname_list=TBLNAME_LIST,
        flagdefault=True,
        flagskw={}):
    """
    autogenerated text main entry point

    Returns:
        tuple : (autogen_fpath, autogen_text)

    CommandLine:
        python ibeis/control/template_generator.py
    """
    # Filepath info
    autogen_fpath, autogen_rel_fpath, autogen_modname = get_autogen_modpaths()
    # Build functions and constant containers
    tup = build_templated_funcs(ibs, autogen_modname, tblname_list,
                                flagdefault=flagdefault, flagskw=flagskw)
    constant_list_, tblname2_functype2_func_list = tup
    # Combine into a text file
    autogen_text = postprocess_and_combine_templates(
        autogen_rel_fpath, constant_list_, tblname2_functype2_func_list, flagskw)
    # Return path and text
    return autogen_fpath, autogen_text


def main(ibs, verbose=True):
    """
    CommandLine:
        python ibeis/control/template_generator.py --tbls annotations --Tcfg with_getters:True strip_docstr:True
        python ibeis/control/template_generator.py --tbls annotations --tbls annotations --Tcfg with_getters:True strip_docstr:False with_columns:False

        python ibeis/control/template_generator.py
        python ibeis/control/template_generator.py --dump-autogen-controller
        gvim ibeis/control/_autogen_ibeiscontrol_funcs.py
        python dev.py --db testdb1 --cmd
        %run dev.py --db testdb1 --cmd
    """
    # Parse command line args
    dowrite = ut.get_argflag('--dump-autogen-controller')
    tblname_list = ut.get_argval(('--autogen-tables', '--tbls'), type_=list, default=TBLNAME_LIST)
    # Parse dictionary flag list
    template_flags = ut.get_argval(('--Tcfg', '--template-config'), type_=list, default=[])

    # Processes command line args
    flagskw = {}
    if len(template_flags) > 0:
        flagdefault = False
        flagskw['with_decor'] = False
        flagskw['with_footer'] = False
        flagskw['with_header'] = False
        flagskw.update(ut.parse_cfgstr_list(template_flags))
        for flag in six.iterkeys(flagskw):
            if flagskw[flag] in ['True', 'On', '1']:
                flagskw[flag] = True
            elif flagskw[flag] in ['False', 'Off', '0']:
                flagskw[flag] = False
            else:
                pass
                #flagskw[flag] = False
    else:
        flagdefault = True

    for tblname in tblname_list:
        assert tblname in tablename2_tbl

    # Autogenerate text
    autogen_fpath, autogen_text = get_autogen_text(tblname_list=tblname_list,
                                                   flagdefault=flagdefault,
                                                   flagskw=flagskw)

    # output to disk or stdout
    if dowrite:
        ut.write_to(autogen_fpath, autogen_text)

    if not ut.QUIET and (not dowrite or verbose):
        print(autogen_text)
    #return locals()


if __name__ == '__main__':
    """
    CommandLine:
        python ibeis/control/template_generator.py
        python ibeis/control/template_generator.py --dump-autogen-controller
    """
    if 'ibs' not in vars():
        import ibeis
        ibs = ibeis.opendb('testdb1')
    main(ibs)
    #exec(ut.execstr_dict(locals_))