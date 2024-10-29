def func(a, b=[]):
    b.append(a)
    return b

print(func(1))
print(func(2))
print(func(3))