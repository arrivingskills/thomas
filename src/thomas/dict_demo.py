import json
person = '{"name": "andy", "age": 42, "height": 72.5, "hair": "brown"}'
print(type(person))
person = json.loads(person)
print(type(person))