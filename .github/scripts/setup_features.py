import toml
import os

cargoPath = 'bindings/c/Cargo.toml'

with open(cargoPath, 'r') as f:
    cargo_toml = toml.load(f)

enabled_features = os.environ.get('OPENDAL_FEATURES', '').split(',')

opendal_features = []
for feature in enabled_features:
    if feature.strip():
        opendal_features.append(feature.strip())

cargo_toml['dependencies']['opendal']['features'] = opendal_features

with open(cargoPath, 'w') as f:
    toml.dump(cargo_toml, f)
