#include <stdio.h>

int global_counter = 0;

struct Point {
    int x;
    int y;
};

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

int fibonacci(int n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

int compute(int x, int y, int flag) {
    int result = 0;
    int temp = 0;
    struct Point p;
    p.x = x;
    p.y = y;

    if (flag > 0) {
        temp = add(x, y);
        result = multiply(temp, 2);
    } else {
        temp = multiply(x, y);
        result = add(temp, 10);
    }

    for (int i = 0; i < 5; i = i + 1) {
        if (i % 2 == 0) {
            result = result + i;
        } else {
            result = result - i;
        }
    }

    int j = 0;
    while (j < 3) {
        result = result + j;
        j = j + 1;
    }

    global_counter = global_counter + result;
    return result;
}

int nested_calls(int n) {
    if (n <= 0) {
        return 0;
    }
    int a = factorial(n);
    int b = fibonacci(n);
    int c = compute(a, b, n % 2);
    return c + nested_calls(n - 1);
}

void process_array(int *arr, int size) {
    int i = 0;
    while (i < size) {
        arr[i] = arr[i] * 2;
        i = i + 1;
    }
}

int main() {
    int a = 5;
    int b = 7;
    int flag = 1;
    int arr[5] = {1, 2, 3, 4, 5};
    struct Point p1;
    p1.x = 10;
    p1.y = 20;

    int sum = add(a, b);
    int prod = multiply(a, b);
    int fact = factorial(6);
    int fib = fibonacci(8);

    int comp = compute(sum, prod, flag);
    int nested = nested_calls(3);

    process_array(arr, 5);

    printf("Sum: %d\n", sum);
    printf("Product: %d\n", prod);
    printf("Factorial(6): %d\n", fact);
    printf("Fibonacci(8): %d\n", fib);
    printf("Compute: %d\n", comp);
    printf("Nested: %d\n", nested);
    printf("Global counter: %d\n", global_counter);

    return 0;
}