import fastcat

f = fastcat.FastCat(language='pt')

print(f.get_current_language())

# Initializes the redis database with Wiki data
f.load(verbose=3)

# Sample usage
f.broader("Portugal")

print('Done')
