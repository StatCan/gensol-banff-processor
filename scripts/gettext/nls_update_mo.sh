# nls_update_mo.sh
# Generates `.mo` file from `.po` file for all supported languages.  

source nls_variables.sh

# English
msgfmt --output-file=${mo_path_en} ${po_path_en}

# French
msgfmt --output-file=${mo_path_fr} ${po_path_fr}
