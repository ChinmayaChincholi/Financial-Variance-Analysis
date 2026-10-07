"""
Static reference data used by the column-matching scoring engine
(column_scoring.py, metric_block_resolver.py).

Everything here is a plain, hand-maintained list/dict -- no network calls,
no external data files -- so the whole ingestion layer stays usable in a
fully offline desktop app.

IMPORTANT: the gazetteers below are STARTER lists, not exhaustive. They
cover the country/region conventions most common in business datasets
(full names, common abbreviations, ISO-ish codes, continent/sales-region
codes). Real client datasets will eventually contain values these lists
don't recognize -- when that happens the gazetteer signal simply
contributes less (see column_scoring.py), it doesn't error out. Extend
these sets as real datasets surface new conventions; this file is the
single place to do that.
"""

# ---------------------------------------------------------------------------
# Header-text synonym dictionaries.
# Matched via normalized token overlap + fuzzy ratio (see column_scoring.py),
# so close variants ("Proj Name", "project_name") don't need to be listed
# verbatim -- only the canonical/common forms need to be here.
# ---------------------------------------------------------------------------

PROJECT_HEADER_SYNONYMS = {
    "project", "project name", "proj", "proj name", "service", "service name",
    "product", "product name", "engagement", "engagement name", "initiative",
    "job", "job name", "account", "workstream", "deal", "deal name",
}

REGION_HEADER_SYNONYMS = {
    "region", "area", "zone", "location", "territory", "geo", "geography",
    "market", "place", "country", "state", "branch", "office", "site",
    "district", "province",
}

REVENUE_HEADER_SYNONYMS = {
    "revenue", "rev", "income", "sales", "turnover", "billing", "billed",
    "invoiced", "invoice amount",
}

COST_HEADER_SYNONYMS = {
    "cost", "costs", "expense", "expenses", "expenditure", "spend", "spent",
    "cogs", "outflow",
}

# ---------------------------------------------------------------------------
# Value gazetteers for the Region signal.
# Lower-cased on lookup; keep these lower-cased here for direct comparison.
# ---------------------------------------------------------------------------

COUNTRY_NAMES = {
    "india", "united states", "usa", "us", "united kingdom", "uk", "germany",
    "france", "italy", "spain", "canada", "australia", "japan", "china",
    "brazil", "mexico", "netherlands", "switzerland", "sweden", "norway",
    "denmark", "finland", "poland", "ireland", "belgium", "austria",
    "portugal", "greece", "singapore", "malaysia", "indonesia", "thailand",
    "vietnam", "philippines", "south korea", "korea", "taiwan", "hong kong",
    "new zealand", "south africa", "nigeria", "egypt", "saudi arabia",
    "united arab emirates", "uae", "qatar", "israel", "turkey", "russia",
    "ukraine", "argentina", "chile", "colombia", "peru", "pakistan",
    "bangladesh", "sri lanka", "nepal",
}

# Common ISO-alpha2 / alpha3 / business-shorthand country and hub codes seen
# in real ERP/finance exports. Not exhaustive -- extend as needed.
COUNTRY_CODES = {
    "in", "ind", "us", "usa", "uk", "gbr", "gb", "de", "ger", "deu", "fr",
    "fra", "it", "ita", "es", "esp", "ca", "can", "au", "aus", "jp", "jpn",
    "cn", "chn", "br", "bra", "mx", "mex", "nl", "nld", "ch", "che", "se",
    "swe", "no", "nor", "dk", "dnk", "fi", "fin", "pl", "pol", "ie", "irl",
    "be", "bel", "at", "aut", "pt", "prt", "gr", "grc", "sg", "sgp", "my",
    "mys", "id", "idn", "th", "tha", "vn", "vnm", "ph", "phl", "kr", "kor",
    "tw", "twn", "hk", "hkg", "nz", "nzl", "za", "zaf", "ng", "nga", "eg",
    "egy", "sa", "sau", "ae", "uae", "qa", "qat", "il", "isr", "tr", "tur",
    "ru", "rus", "ua", "ukr", "ar", "arg", "cl", "chl", "co", "col", "pe",
    "per", "pk", "pak", "bd", "bgd", "lk", "lka", "np", "npl", "mme", "usw",
    "use", "usn", "uss", "ukg",
}

# US state 2-letter codes and full names -- kept separate from country codes
# because seeing a lot of these in a column is a signal AWAY FROM "Region"
# and toward a finer-grained "State" field, per column_scoring.py.
US_STATE_CODES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy",
}

# Continent / sales-region rollup codes -- common in enterprise datasets as
# a HIGHER-level grouping than country (EMEA, APAC, etc.).
CONTINENT_REGION_CODES = {
    "emea", "amer", "apac", "amea", "latam", "mea", "anz", "na", "eu",
    "imea", "europe", "asia", "africa", "oceania",
}

# Union used for the primary "does this look like a region value" check.
ALL_REGION_VALUE_TOKENS = COUNTRY_NAMES | COUNTRY_CODES | CONTINENT_REGION_CODES