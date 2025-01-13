"""A program to convert Banff excel spreadsheet to XML files.

Statistics Canada 2024
K Williamson
"""

import argparse
import html
import sys
import warnings
from argparse import RawTextHelpFormatter
from pathlib import Path

import pandas as pd

import banffprocessor
import banffprocessor.processor_logger as plg
from banffprocessor.nls import _

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# Setup local log for this module

# NOTE: If using the normal get_processor_child_logger() function here, the logger
# will use the regular output handlers. This causes issues when a file location is
# set prior to running this module, as all outputs here will go to the same location.
# For pytest in particular, this causes logs from tests for this module to pile up
# at the end of the last log file created. Instead the get_child_stream_logger()
# function returns a logger that does not propagate to the parent and only logs
# to the console.
log_lcl = plg.get_child_stream_logger("metadata_excel_to_xml")

def convert_excel_to_xml(in_file: str, out_dir: str | None = None) -> None:
    """Create XML files from an Excel file that was created using the Banff Processor Metadata Template.

    In order to facilitate the creation of Banff Processor metadata, users can create the metadata in
    Excel using the Banff Processor metadata template. This function reads in the Excel file indicated by
    the infile parameter and writes XML files to the directory indicated in out_dir.
    """
    # Verify in_file is indeed a file
    if not Path(in_file).is_file():
        msg = _("{} does not exist or is not a file.").format(in_file)
        log_lcl.exception(msg)
        raise FileNotFoundError(msg)

    # If no output directory was provided, the default is the same location as the Excel file
    if out_dir is None:
         out_dir = Path(in_file).parent
    elif not Path(out_dir).is_dir():
        msg = _("{} does not exist or is not a directory.").format(out_dir)
        log_lcl.exception(msg)
        raise NotADirectoryError(msg)

    # Create dictionaries from the Excel sheets and the expected columns
    excel_sheets = pd.read_excel(in_file, sheet_name=None)
    sheet_cols = _create_column_dict()

    msg = _("Creating XML files for: {}\n").format(in_file)
    log_lcl.info(msg)

    # foreach sheet in the spreadsheet
    for sheet in sheet_cols:
        if sheet not in excel_sheets:
            continue

        sheet_df = excel_sheets[sheet]

        # skip sheets with no data
        if len(sheet_df.index) == 0:
            continue

        fpath = Path(out_dir).joinpath(sheet.casefold() + ".xml")
        msg = f"  {sheet:<25} {fpath}"
        log_lcl.info(msg)

        _write_xml_data_file(sheet, sheet_df, sheet_cols[sheet], fpath)

    log_lcl.info(_("\nXML files have been created sucessfully.\n"))

def _write_xml_data_file(sheet_name: str, sheet_df: pd.DataFrame, columns: tuple, file_name: str) -> None:
    xml_data = ['<?xml version="1.0" encoding="ISO-8859-1"?>\n']
    xml_data.append("<banffProcessor>\n")
    for row in sheet_df.index:
        xml_data.append(f"<{sheet_name.casefold()}>\n") #opening element tag
        for column in sheet_df.columns:
            if column in columns:
                cell_value = str(sheet_df[column][row])
                if cell_value not in ("", "nan"):
                    #escape special chars
                    cell_value = html.escape(cell_value)

                    # drop trailing zeros
                    if cell_value.endswith(".0"):
                        cell_value = cell_value[0: len(cell_value)-2]

                    xml_data.append(f"<{column}>{cell_value}</{column}>\n")
        xml_data.append(f"</{sheet_name.casefold()}>\n")
    xml_data.append("</banffProcessor>\n")

    # write to the xml file
    with Path(file_name).open("w") as f:
        for line in xml_data:
            f.write(line)

def _create_column_dict() -> dict:
    """Create a directory for the columns of the banff processor metadata.

    A dictionary is created with an entry for each banff processor metadata file. The entry was all the possible columns for each
    metadata file.
    """
    sheet_cols = {}
    sheet_cols["JOBS"] = ("jobid", "seqno", "controlid", "process", "specid", "editgroupid", "byid","acceptnegative")
    sheet_cols["EDITS"] = ("editid", "leftside", "operator", "rightside", "modifier")
    sheet_cols["EDITGROUPS"] = ("editgroupid", "editid")
    sheet_cols["VERIFYEDITSSPECS"] = ("specid", "imply", "extremal")
    sheet_cols["OUTLIERSPECS"] = ("specid", "method", "side", "varid",
                                  "withid", "mii", "mei", "mdm","exponent",
                                  "sigma", "betai", "betae", "startcentile",
                                  "minobs","acceptzero", "weight", "dataexclvar")
    sheet_cols["ERRORLOCSPECS"] = ("specid", "cardinality", "timeperobs", "weightid")
    sheet_cols["DONORSPECS"] = ("specid", "mindonors", "pcentdonors", "n", "eligdon",
                                "random", "nlimit", "mrl", "dataexclvar", "mustmatchid",
                                "posteditgroupid")
    sheet_cols["ESTIMATORS"] = ("estimatorid", "seqno", "fieldid", "auxvariables",
                                "weightvariable", "variancevaraible", "varianceexponent",
                                "varianceperiod", "excludeimputed", "excludeoutliers",
                                "countcriteria", "percentcriteria", "randomerror", "algorithmname")
    sheet_cols["ESTIMATORSPECS"] = ("specid", "dataexclvar", "histexclvar", "estimatorid")
    sheet_cols["PRORATESPECS"] = ("specid", "decimal", "lowerbound", "upperbound", "modifier", "method")
    sheet_cols["MASSIMPUTATIONSPECS"] = ("specid", "mindonors", "pcentdonors", "random", "nlimit",
                                         "mrl", "mustimputeid", "mustmatchid")
    sheet_cols["ALGORITHMS"] = ("algorithmname", "type", "status", "formula", "description")
    sheet_cols["EXPRESSIONS"] = ("expressionid", "expressions")
    sheet_cols["USERVARS"] = ("process", "specid", "var", "value")
    sheet_cols["VARLISTS"] = ("varlistid", "seqno", "fieldid")
    sheet_cols["WEIGHTS"] = ("weightid", "fieldid", "weight")
    sheet_cols["PROCESSCONTROLS"] = ("controlid", "targetfile", "parameter", "value")
    sheet_cols["PROCESSOUTPUTS"] = ("process", "output_name")
    return sheet_cols

def get_args(args:list | str | None = None) -> argparse.ArgumentParser:
    """Create an argument parser.

    Example args -> ["my_filename.xlsx", "-o", "/my/out/folder", "-l", "fr"]
    """
    parser = argparse.ArgumentParser(description="Create XML files from an Excel spreadsheet that was created based on the Banff Processor metadata templete.\n\n"
                                     "Créer des fichiers XML à partir d'une feuille de calcul Excel créée sur la base du modèle de métadonnées du processeur Banff.",
                                     formatter_class=RawTextHelpFormatter)

    # First argument is positional, required by default
    parser.add_argument("filename", help="Filename of Excel file to convert.\n"
                        "Le nom du fichier Excel à convertir.")

    # Second argument is set by flag
    parser.add_argument("-o", "--outdir", help="The directory where output files will be written. \n"
                        "Le répertoire dans lequel les fichiers de sortie seront écrits.")

     # Second argument is set by flag
    parser.add_argument("-l", "--lang", default="en",
                        help="Set the language, supported langauges are en for English and fr for French. \n"
                        "Définissez la langue, les langues prises en charge sont en pour l'anglais et fr pour le français.")

    return parser.parse_args(args)

def main(iargs: list | str | None = None) -> None:
    """Call the convert_excel_to_xml function.

    Used when running this module from the command line. Created to faciliate testing.
    """
    if iargs is None:
        iargs = sys.argv[1:]

    args = get_args(iargs)

    banffprocessor.set_language(banffprocessor.SupportedLanguage[args.lang])
    convert_excel_to_xml(args.filename, args.outdir)

def init() -> None:
    """Call the main function.

    Used when running this module from the command line. Created to faciliate testing.
    """
    if __name__  == "__main__":
        sys.exit(main())

init()
