create and sourcing env : 

all the above command must be execute in the *ingestor* file

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
.venv\Scripts\activate      # Windows PowerShell
```

then execute this command : 

``` 
pip install -e .
```

if everything is good a file Crypto_Viz.egg-info

## Reset data sources : 

To reset data sources : 

*data/raw*

*data/clean*

*chk*

You need to open your docker scraper terminal and launch this command : 

``` 
python tools/resetdata.py
```

you might see these type of error : "is not dir or dir does not exist" if the dir is already empty