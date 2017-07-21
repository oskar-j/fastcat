import fastcat

f = fastcat.FastCat(language='pt')

print(f.get_current_language())

f.load(verbose=3)

print('Done')
