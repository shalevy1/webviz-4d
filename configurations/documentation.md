### Documentation
The full user documentation has not yet been finalized, but some useful information is given below.
   
#### Well data
- Drilled wells have been extracted from the REP database and are stored in directory:
    - <folder>/webviz-4d/well_data
- AMAP wells have been copied from the Coviz project and are stored in directory:
    - <folder>/webviz-4d/well_data/AMAP
- Planned wells have been extracted from DSG and and are stored in directory: 
    - <folger>/webviz-4d/well_data/Planned   
    - Production/injection volumes have been extracted from PDM Omnia and aggregated volumes in the available 4D intervals are stored as csv-files (BORE_<fluid>_VOL.csv) in directory:
       - <folder>/webviz-4d/well_data/ 
    

#### Configuration
Two configuration files are used to create this application:

- config_template.yaml: This is a standard webviz configuration file
- settings_tempalte.yaml: This is an optional configuration file to specify display settings for WebViz-4D
  - This file points to a spreadsheet file that can be used to customize colormaps and plot limits for the attribute maps
    - <folder>/configurations/attribute_maps.csv




