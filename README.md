# Thomas - RAG Application with Ollama

A Python-based Retrieval-Augmented Generation (RAG) application using ChromaDB for vector storage and Ollama for LLM inference.

## 🪟 Windows Users - START HERE!

**This application has Windows-specific requirements and configuration steps.**

👉 **See [WINDOWS_QUICKSTART.md](WINDOWS_QUICKSTART.md)** for fast setup (5 minutes)  
👉 **See [HOWTO.md](HOWTO.md)** for detailed troubleshooting and architecture

### Quick Test
After setup, run the connection diagnostic tool:
```bash
python test_windows_connection.py
```

---

## Features

- Fetches RSS feeds from FINMA (Swiss Financial Market Supervisory Authority)
- Creates embeddings and stores them in ChromaDB
- Performs semantic search on stored documents
- Uses Ollama (llama3.1) for response generation
- Cross-platform support (macOS, Linux, Windows)

---

## Python Exercises (Original Content)

Positive, Negative, or Zero Counter
Create a list of at least 10 integers (mix of positive, negative, and zero).
Use a for loop to go through each number.
Use if/elif/else to count how many are: positive, negative, and zero.
At the end, print the three counts.

Find the Largest and Smallest Number
Make a list of at least 8 numbers.
Use a for loop to find the largest and smallest numbers without using max() or
min().
Use if statements to update “current max” and “current min” variables.
Print the largest and smallest numbers.

Filter Passing Scores
Create a list of scores (integers from 0 to 100).
Use a for loop to go through each score.
If the score is 50 or above, add it to a new list called passing.
After the loop, print the passing list.

Word Search in a List
Create a list of 8–10 words (your choice).
Ask the user to type a word.
Use a for loop and an if statement to check if the word is in the list.
If found, print "Found!"; otherwise, after the loop, print "Not found.".

Remove Short Words
Create a list of words.
Ask the user for a minimum length (an integer).
Use a for loop and if statements to build a new list containing only the words
with length greater than or equal to the given number.
Print the new list.

Number Guessing Hints (List of Attempts)
Choose a secret number between 1 and 20 (hardcode it in the code).
Create an empty list to store guesses.
Use a for loop that runs up to 5 times (5 attempts).
Each time, ask the user to guess the number and store the guess in the list.
Use if/elif/else to print:
"Too low" if the guess is less than the secret number
"Too high" if greater
"Correct!" if equal (and then stop the loop early if you want)
At the end, print the list of all guesses.

Multiples Filter
Create a list of integers from 1 to 30 (you can either type them or generate
them).
Ask the user for a number n.
Use a for loop and an if statement to print only the numbers in the list that
are multiples of n (i.e., number % n == 0).

Category Labels for Ages
Create a list of ages (integers, e.g., [3, 12, 17, 25, 40, 70]).
Use a for loop to go through each age.
Use if/elif/else to decide:
"Child" for age < 13
"Teen" for 13–17
"Adult" for 18–64
"Senior" for 65+
For each age, print something like "Age 25: Adult".

Vowel Counter in Words List
Create a list of words.
For each word (using a for loop), count how many vowels it has (a, e, i, o, u,
optionally uppercase too).
Use an inner for loop over the letters of the word and an if to check if the
letter is a vowel.
For each word, print the word and its vowel count.

Index of First Even Number
Create a list of integers.
Use a for loop with an index (e.g., for i in range(len(numbers)):).
Use an if statement to find the first even number in the list.
When you find it, print its index and value, then stop checking the rest of the
list.
If no even number is found, print a message like "No even numbers".


# --

Here are the 10 practical exercises for practicing `if` statements, `for` loops, lists, and functions, presented without the solutions.
### 1. The Even Number Filter
- **Goal:** Create a function called `filter_evens` that takes a list of integers as an argument. The function should create and return a new list containing only the even numbers from the original list.
- **Key Concepts:** Iterating through a list with `for`, using the modulo operator `%` to check for divisibility inside an `if` statement.

### 2. The Grade Calculator
- **Goal:** Write a function called `assign_grades` that accepts a list of student scores (numbers 0-100). Loop through the scores and print the corresponding letter grade for each:
    - 90 and above: "A"
    - 80 to 89: "B"
    - 70 to 79: "C"
    - Below 70: "F"

- **Key Concepts:** Using `if-elif-else` chains inside a `for` loop.

### 3. Find the Maximum (Manual)
- **Goal:** Write a function called `find_max` that takes a list of numbers and returns the largest number. **Constraint:** You cannot use Python's built-in `max()` function. You must implement the logic yourself.
- **Key Concepts:** Creating a variable to track the "current winner" and updating it as you loop through the list.

### 4. The Shopping List Checker
- **Goal:** Define a list called `stock` with 4-5 items (e.g., "apple", "milk"). Write a function that takes a different list (a user's `shopping_list`) as an argument. Loop through the user's list and print whether each item is currently in stock or out of stock.
- **Key Concepts:** Checking for membership using the `in` keyword combined with `if/else`.

### 5. Word Length Sorter
- **Goal:** Create a function that takes a list of words. It should create two new empty lists: `short_words` and `long_words`. Loop through the input:
    - If a word has fewer than 5 letters, add it to `short_words`.
    - If a word has 5 or more letters, add it to `long_words`.
    - Return both lists at the end.

- **Key Concepts:** Using `len()` to check string length and appending to different lists based on a condition.

### 6. Sum of Positive Numbers
- **Goal:** Write a function called `sum_positives` that accepts a list containing both positive and negative integers (e.g., `[10, -5, 20, -3]`). The function should calculate and return the sum of _only_ the positive numbers.
- **Key Concepts:** Using an "accumulator" variable (like `total = 0`) and an `if` statement to decide when to add to it.

### 7. Count Occurrences (Manual)
- **Goal:** Write a function called `count_target` that takes two arguments: a list of items and a specific "target" value. The function should return the number of times the target appears in the list. **Constraint:** Do not use the built-in `.count()` method.
- **Key Concepts:** incrementing a counter variable inside a conditional loop.

### 8. Reverse "A" Words
- **Goal:** Write a function that takes a list of names (strings). Loop through the list and check if a name starts with the letter "A" (or "a"). If it does, print that name reversed. If it doesn't start with "A", ignore it.
- **Key Concepts:** String slicing `[::-1]` to reverse, and using `.startswith()` or index `[0]` for the condition.

### 9. FizzBuzz (List Version)
- **Goal:** Write a function that generates and returns a list of numbers from 1 to 20. However, apply these rules before adding the number to the list:
    - If the number is divisible by 3, add "Fizz" instead of the number.
    - If the number is divisible by 5, add "Buzz" instead of the number.
    - If divisible by both 3 and 5, add "FizzBuzz".
    - Otherwise, add the number itself.

- **Key Concepts:** Complex logic flow. _Hint: Check for the "FizzBuzz" (divisible by both) condition first!_

### 10. The Password Validator
- **Goal:** Create a function that accepts a list of potential passwords (strings). The function should return a new list containing only the "valid" passwords. A password is valid if:
    1. It is at least 8 characters long.
    2. **AND** it contains at least one number.

- **Key Concepts:** Checking multiple conditions using `and`. You might need a nested loop or a helper check to find if a string contains a digit.
