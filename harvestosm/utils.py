import random, string


def random_name():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(5))