# nls_update_po.sh
# Generates a template `.pot` file by scanning all Python source files with `xgettext`.  
# Then it generates language specific `.po` files.  
#   For English it essentially does nothing, since each message ID is equivalent to the English message.  
#   For French:
#       If no file exists, it creates one from scratch, with all definitions empty
#       If a file exists already it is updated, meaning any existing translations are retained

source nls_variables.sh

# generate template
find ${source_root} -iname "*.py" | xargs xgettext --output=${template_path} --from-code=UTF-8 --language=Python

# English: create new English .po file with msgstr=msgid
msginit --output-file=${po_path_en} --input=${template_path} --locale=en --no-translator
git --no-pager diff --color ${po_path_en}

# French: update if exists, otherwise create empty French po file with empty translations
if [ -f ${po_path_fr} ]; then
    echo "File ${po_path_fr} exists, it will be updated"
    msgmerge --update --backup=off --previous ${po_path_fr} ${template_path}
    git --no-pager diff --color ${po_path_fr}
else
    echo "File ${po_path_fr} does not exists, it will be initialized"
    msginit --output-file=${po_path_fr} --input=${template_path} --locale=fr --no-translator
fi
