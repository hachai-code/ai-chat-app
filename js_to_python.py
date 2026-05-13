"""
Python for JS/TS developers — one file covering the core idioms.
Run with:  python3 js_to_python.py
Requires Python 3.9+.
Note: X | Y union syntax in type hints requires Python 3.10+; we use Union[] here
      so the file runs on 3.9. At the type-checker level both are equivalent.
"""

# ── IMPORTS ──────────────────────────────────────────────────────────────────
# JS: import { reduce } from 'lodash'  /  import fs from 'fs'
# Python has no "default" vs "named" export distinction; everything is a name.
from __future__ import annotations    # enables X | Y syntax in annotations on 3.9
from functools import reduce
from typing import TypedDict, Union   # dict with known shape — like a TS interface
import asyncio                        # stdlib; no npm install needed


# ══════════════════════════════════════════════════════════════════════════════
# 1.  LISTS  (≈ JS arrays)
# ══════════════════════════════════════════════════════════════════════════════

numbers: list[int] = [1, 2, 3, 4, 5]

# map — Python's map() returns a lazy iterator, so wrap in list() to materialise.
# JS:  numbers.map(n => n * 2)
doubled: list[int] = list(map(lambda n: n * 2, numbers))

# Idiomatic Python prefers list comprehensions over map/filter lambdas.
doubled_comp: list[int] = [n * 2 for n in numbers]

# filter
# JS:  numbers.filter(n => n % 2 === 0)
evens: list[int] = list(filter(lambda n: n % 2 == 0, numbers))
evens_comp: list[int] = [n for n in numbers if n % 2 == 0]

# reduce — NOT a built-in; must import from functools (unlike JS Array.prototype.reduce).
# JS:  numbers.reduce((acc, n) => acc + n, 0)
total: int = reduce(lambda acc, n: acc + n, numbers, 0)

# Common array operations
mixed: list[int | str] = [*numbers, "six"]   # spread to concat (see §5)
length: int = len(mixed)                     # JS: mixed.length  — NOT a property here

# Slicing — same semantics as JS .slice() but terser syntax.
# JS:  numbers.slice(1, 3)
sliced: list[int] = numbers[1:3]             # [2, 3]  — end index exclusive, like JS

# Sorting — in-place by default (unlike JS, which also mutates but returns the array).
# JS:  [...numbers].sort((a, b) => b - a)
desc: list[int] = sorted(numbers, reverse=True)   # returns new list; numbers unchanged

print("── Lists ──")
print(doubled, evens, total, sliced, desc)


# ══════════════════════════════════════════════════════════════════════════════
# 2.  DICTS  (≈ JS plain objects / Record<K,V>)
# ══════════════════════════════════════════════════════════════════════════════

# JS:  const user = { name: "Alice", age: 30 }
user: dict[str, str | int] = {"name": "Alice", "age": 30}

# Property access — bracket syntax always works; dot syntax does NOT exist on plain dicts.
# JS:  user.name  or  user["name"]
name_val: str | int = user["name"]

# .get() is the safe-access equivalent of JS optional chaining (?.)
# JS:  user?.role ?? "guest"
role: str | int = user.get("role", "guest")   # type: ignore[assignment]

# TypedDict — closest thing to a TS interface for dicts.
class UserShape(TypedDict):
    name: str
    age: int

typed_user: UserShape = {"name": "Bob", "age": 25}

# Object.keys / Object.values / Object.entries
# JS:  Object.entries(user)
for key, value in user.items():              # .keys(), .values(), .items()
    pass

# Dict comprehension — like Object.fromEntries(arr.map(...))
# JS:  Object.fromEntries(["a","b"].map((k,i) => [k, i]))
indexed: dict[str, int] = {k: i for i, k in enumerate(["a", "b"])}

print("\n── Dicts ──")
print(typed_user, role, indexed)


# ══════════════════════════════════════════════════════════════════════════════
# 3.  ASYNC / AWAIT
# ══════════════════════════════════════════════════════════════════════════════
# Python's async model is cooperative (like JS), single-threaded within an event
# loop, and driven by asyncio rather than the runtime's built-in event loop.
# Key difference: you must explicitly run an event loop (asyncio.run); in Node
# the loop is always running.

async def fetch_data(url: str) -> dict[str, str]:
    # JS:  await fetch(url).then(r => r.json())
    # In real code use:  async with aiohttp.ClientSession() as s: ...
    await asyncio.sleep(0.01)               # simulate I/O
    return {"url": url, "data": "..."}


async def fetch_all(urls: list[str]) -> list[dict[str, str]]:
    # JS:  await Promise.all(urls.map(fetch))
    results = await asyncio.gather(*[fetch_data(u) for u in urls])
    return list(results)


async def main() -> None:
    result = await fetch_data("https://example.com")
    many   = await fetch_all(["https://a.com", "https://b.com"])
    print("\n── Async ──")
    print(result, many)


# ══════════════════════════════════════════════════════════════════════════════
# 4.  DESTRUCTURING
# ══════════════════════════════════════════════════════════════════════════════
# Python calls this "unpacking". It works on any iterable, not just arrays/objects.

# Array / tuple destructuring
# JS:  const [first, second, ...rest] = numbers
first, second, *rest = numbers              # rest captures the tail as a list

# Swap without temp variable — idiomatic Python, not possible as tersely in JS
a, b = 1, 2
a, b = b, a

# Dict unpacking — Python has NO equivalent of JS object destructuring syntax.
# JS:  const { name, age } = user
# Python: you must either index or unpack explicitly.
name_str: str | int = user["name"]         # most common approach
age_val:  str | int = user["age"]

# Function return: return a tuple, unpack at the call site.
def min_max(vals: list[int]) -> tuple[int, int]:
    return min(vals), max(vals)

lo, hi = min_max(numbers)

print("\n── Destructuring / unpacking ──")
print(first, second, rest, lo, hi)


# ══════════════════════════════════════════════════════════════════════════════
# 5.  SPREAD  (≈ JS ... operator)
# ══════════════════════════════════════════════════════════════════════════════

# List spread — same as JS array spread
# JS:  [...a, ...b]
a_list = [1, 2, 3]
b_list = [4, 5, 6]
merged_list: list[int] = [*a_list, *b_list]

# Dict merge — ** unpacks a dict, like JS { ...obj1, ...obj2 }
# JS:  { ...defaults, ...overrides }
defaults: dict[str, int | str] = {"color": "blue", "size": 10}
overrides: dict[str, int | str] = {"size": 20, "weight": 5}
merged_dict: dict[str, int | str] = {**defaults, **overrides}   # later key wins

# Spread into function args — *args for positional, **kwargs for keyword
# JS:  Math.max(...numbers)
maximum: int = max(*numbers)               # or simply max(numbers)

def greet(first_name: str, last_name: str) -> str:
    return f"Hello {first_name} {last_name}"

parts = {"first_name": "Ada", "last_name": "Lovelace"}
greeting: str = greet(**parts)             # JS:  greet(...Object.values(parts))

print("\n── Spread ──")
print(merged_list, merged_dict, greeting)


# ══════════════════════════════════════════════════════════════════════════════
# 6.  CLASSES
# ══════════════════════════════════════════════════════════════════════════════
# Biggest difference: `self` is explicit (not implicit `this`); constructors are
# named `__init__`, not the class name; private fields use _ convention (no hard
# enforcement unless you use name-mangling with __).

class Animal:
    # Class variable (≈ static property)
    # JS:  static count = 0
    count: int = 0

    def __init__(self, name: str, sound: str) -> None:
        # JS:  constructor(name, sound) { this.name = name; ... }
        self.name  = name
        self._sound = sound              # _ prefix = "private by convention"
        Animal.count += 1

    # JS:  get sound() { return this._sound }
    @property
    def sound(self) -> str:
        return self._sound

    # JS:  set sound(v) { this._sound = v }
    @sound.setter
    def sound(self, value: str) -> None:
        self._sound = value

    # JS:  toString() / [Symbol.toPrimitive]
    def __repr__(self) -> str:
        return f"Animal(name={self.name!r})"

    # Static method — JS:  static create(name) { ... }
    @staticmethod
    def create(name: str) -> "Animal":
        return Animal(name, "...")

    # Class method (receives class, not instance) — no direct JS equivalent
    @classmethod
    def reset_count(cls) -> None:
        cls.count = 0


class Dog(Animal):                        # JS:  class Dog extends Animal
    def __init__(self, name: str) -> None:
        super().__init__(name, "woof")    # JS:  super(name, "woof")

    def speak(self) -> str:
        return f"{self.name} says {self.sound}"

    # Dunder methods implement operator overloading / protocols.
    # JS has no equivalent (Symbol.iterator aside).
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dog) and self.name == other.name


dog1 = Dog("Rex")
dog2 = Dog("Rex")

print("\n── Classes ──")
print(dog1.speak(), dog1 == dog2, Animal.count, repr(dog1))


# ══════════════════════════════════════════════════════════════════════════════
# 7.  MODULES  (note — single file, so just the concepts)
# ══════════════════════════════════════════════════════════════════════════════
# JS:  export const PI = 3.14           Python:  PI = 3.14  (every name is importable)
# JS:  export default function foo(){}  Python:  no default export; import by name
# JS:  import PI from './math'          Python:  from math_module import PI
# JS:  import * as math from './math'   Python:  import math_module as math
#
# __all__ is the closest thing to controlling what "export *" exposes:
#   __all__ = ["PI", "Dog"]
#
# Packages are directories with an __init__.py (though implicit namespace packages
# work without it in Python 3.3+).
#
# There is no tree-shaking; the whole module is executed on first import (cached
# in sys.modules on subsequent imports — same as Node's require() caching).


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
# JS:  if (require.main === module) { ... }   or just top-level in ESM
# Python:  the __name__ guard is the canonical pattern.
if __name__ == "__main__":
    asyncio.run(main())
