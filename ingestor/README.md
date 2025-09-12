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