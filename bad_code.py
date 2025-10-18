MULTIPLICATEUR = 5

def multiply_array(array):
    result = []
    for x in array:
        result.append(x * MULTIPLICATEUR)  # ⚠️ usage direct d'une globale dans une boucle
    return result


def multiply_array_ok(array):
    multiplicateur = MULTIPLICATEUR
    result = []
    for x in array:
        result.append(x * multiplicateur)  # ✅ local, pas de problème
    return result
