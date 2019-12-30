import ctags
from flask import g, request, safe_join, url_for
import os.path
from urllib.parse import urlsplit, urlunsplit

from i2p2www import (
    CANONICAL_DOMAIN,
    CURRENT_I2P_VERSION,
    CURRENT_I2P_FIREFOX_PROFILE_VERSION,
    PROPOSAL_DIR,
    RTL_LANGS,
    SUPPORTED_LANGS,
    SUPPORTED_LANG_NAMES,
    SPEC_DIR,
    STATIC_DIR,
    app,
)

INPROXY = '.xyz' # http://zzz.i2p/topics/1771-i2p-xyz-inproxy

I2P_TO_CLEAR = {
    'i2pforum.i2p': 'i2pforum.net', # New I2P Forum
    'trac.i2p2.i2p': 'trac.i2p2.de',
    'mail.i2p': 'i2pmail.org',
    'lists.i2p': 'lists.i2p.email',
    'i2p-javadocs.i2p': 'docs.i2p-projekt.de/javadoc', # Hacky to include the path, but it works!
    'echelon.i2p/javadoc': 'docs.i2p-projekt.de/javadoc', # Hacky to include the path, but it works!
    'stats.i2p': 'stats.i2p', # Inproxy disabled at request of site owner
    'zzz.i2p': 'zzz.i2p',     # Inproxy disabled at request of site owner
    }

CLEAR_HTTP = [
    'stats.i2p',
    'zzz.i2p',
    ]

#BROWSER_NAME = 'I2P Rhizome'
BROWSER_NAME = 'I2P Browser'
BROWSER_VERSION = 'beta7'
#BROWSER_SUBTITLE = 'Communication Security Toolkit'
BROWSER_SUBTITLE = ''
BROWSER_FILE = 'i2pbrowser-install'

####################
# Template functions

@app.context_processor
def utility_processor():
    _ctags = ctags.CTags(os.path.join(SPEC_DIR, 'spectags'))
    kinds = {
        't': 'type',
        's': 'struct',
        'm': 'msg',
        }

    # Shorthand for getting a site url
    def get_site_url(path=None, external=False):
        lang = 'en'
        if hasattr(g, 'lang') and g.lang:
            lang = g.lang
        if path:
            return url_for('site_show', lang=lang, page=path, _external=external)
        else:
            return url_for('site_show', lang=lang, _external=external)

    def get_spec_url(name):
        url = url_for('spec_show', name=name, _external=True)
        # Remove ?lang=xx
        if '?' in url:
            url = url[:url.index('?')]
        return url

    def get_proposal_url(identifier):
        name = None
        for f in os.listdir(PROPOSAL_DIR):
            if f.startswith(identifier):
                name = f[:-4]
                break
        if not name:
            return ''
        url = url_for('proposal_show', name=name, _external=True)
        # Remove ?lang=xx
        if '?' in url:
            url = url[:url.index('?')]
        return url

    def get_ctags_url(value):
        filename, kind = _lookup_ctag(value)
        # Handle message types
        if not kind and value.endswith('Message'):
            value = value[:-7]
            filename, kind = _lookup_ctag(value)
        if kind:
            specname, _ = os.path.splitext(filename)
            url = get_spec_url(specname)
            return '%s#%s-%s' % \
                (url, kinds[kind], value.lower())
        else:
            return ''

    def _lookup_ctag(token):
        entry = ctags.TagEntry()
        if _ctags.find(entry, token, 0):
            return entry['file'], entry['kind']
        else:
            return None, None

    # Shorthand for getting a language-specific url
    def get_url_with_lang(endpoint, **args):
        lang = 'en'
        if hasattr(g, 'lang') and g.lang:
            lang = g.lang
        return url_for(endpoint, lang=lang, **args)

    def is_rtl_lang(lang=None):
        if not lang:
            if hasattr(g, 'lang') and g.lang:
                lang = g.lang
            else:
                lang = 'en'
        return lang in RTL_LANGS

    # Get a specific language flag, or the flag for the current language
    def get_flag(lang=None):
        if not lang:
            if hasattr(g, 'lang') and g.lang:
                lang = g.lang
            else:
                lang = 'en'
        return url_for('static', filename='images/flags/'+lang+'.png')

    # Provide the canonical link to the current page
    def get_canonical_link():
        # Canonical domain should always be HTTPS
        return 'https://' + CANONICAL_DOMAIN + request.path

    # Convert an I2P url to an equivalent clearnet one
    def convert_url_to_clearnet(value):
        if not value.endswith('.i2p'):
            # The url being passed in isn't an I2P url, so just return it
            return value
        if request.headers.get('X-I2P-Desthash') and not request.headers.get('X-Forwarded-Server'):
            # The request is from within I2P, so use I2P url
            return value
        # The request is either directly from clearnet or through an inproxy
        try:
            # Return the known clearnet url corresponding to the I2P url
            return I2P_TO_CLEAR[value]
        except KeyError:
            # The I2P site has no known clearnet address, so use an inproxy
            return value + INPROXY

    # Convert an I2P url to an equivalent clearnet one, including HTTPS if necessary
    def convert_url_to_clearnet_inc_https(value):
        parts = urlsplit(value)
        if not parts[1].endswith('.i2p'):
            # The url being passed in isn't an I2P url, so just return it
            return value
        if request.headers.get('X-I2P-Desthash') and not request.headers.get('X-Forwarded-Server'):
            # The request is from within I2P, so use I2P url
            return value
        # The request is either directly from clearnet or through an inproxy
        try:
            # Return the known clearnet url corresponding to the I2P url
            scheme = parts[0]
            host = I2P_TO_CLEAR[parts[1]]
            if scheme == 'http' and host not in CLEAR_HTTP:
                scheme = 'https'
            return urlunsplit([scheme, host] + list(parts[2:]))
        except KeyError:
            # The I2P site has no known clearnet address, so use an inproxy
            return urlunsplit([parts[0], parts[1] + INPROXY] + list(parts[2:]))

    # Convert a paginated URL to that of another page
    def url_for_other_page(page):
        args = request.view_args.copy()
        args['page'] = page
        return url_for(request.endpoint, **args)

    # Change the theme of the current page
    def change_theme(theme):
        args = {}
        if request.view_args:
            args = request.view_args.copy()
        args['theme'] = theme
        if request.endpoint:
            return url_for(request.endpoint, **args)
        # Probably a 404 error page
        return url_for('main_index', **args)

    # Shorthand for getting the logo for the current theme
    def get_logo_for_theme():
        logo = 'styles/' + g.theme + '/images/i2plogo.svg'
        if not os.path.isfile(safe_join(STATIC_DIR, logo)):
            logo = 'images/i2plogo.svg'
        return logo

    def get_current_version(string=None, ver=None):
        if string:
            if ver:
                return string % ver
            return string % CURRENT_I2P_VERSION
        return CURRENT_I2P_VERSION

    def get_current_firefox_profile_version(string=None, ver=None):
        if string:
            if ver:
                return string % ver
            return string % CURRENT_I2P_FIREFOX_PROFILE_VERSION
        return CURRENT_I2P_FIREFOX_PROFILE_VERSION

    def browser_current_version():
        return BROWSER_VERSION

    def browser_short_name():
        return BROWSER_NAME

    def browser_suffix_name():
        return BROWSER_SUBTITLE

    def browser_filename_name(version="beta7", platform="linux", series="2.0", language="en-US", exe=None):
        return 'i2pbrowser-install-' + platform + "-" + series + "-" + version + "_" + language + exe

    return dict(i2pconv=convert_url_to_clearnet,
                i2pclr=convert_url_to_clearnet_inc_https,
                url_for_other_page=url_for_other_page,
                change_theme=change_theme,
                logo_url=get_logo_for_theme,
                site_url=get_site_url,
                spec_url=get_spec_url,
                proposal_url=get_proposal_url,
                ctags_url=get_ctags_url,
                get_url=get_url_with_lang,
                is_rtl=is_rtl_lang,
                get_flag=get_flag,
                ver=get_current_version,
                pver=get_current_firefox_profile_version,
                canonical=get_canonical_link,
                browser_version=browser_current_version,
                browser_name=browser_short_name,
                browser_postname=browser_suffix_name,
                browser_filename=browser_filename_name,
                supported_langs=SUPPORTED_LANGS,
                lang_names=SUPPORTED_LANG_NAMES)
