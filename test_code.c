// ============================================================
//  Complete C program covering all grammar rules of the project
//  (grammer.txt) – without using printf (output via return values)
// ============================================================

// --- Struct definition (struct_prefix) ---
struct Point {
    int x;
    int y;
};

// --- Struct with pointer fields ---
struct Node {
    int value;
    struct Node* next;
};

// --- Global variable declarations (non_struct_decl) ---
int global_counter = 0;
float pi = 3.14159f;
char* message = "Hello";
double precision = 1e-10;

// --- Function prototypes (function declarations) ---
int add(int a, int b);
void print_point(struct Point p);
struct Point* create_point(int x, int y);
int sum_array(int arr[], int size);

// --- Function definition with parameters and local vars ---
int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

// --- Function using pointers, structs, and member access ---
void increment_point(struct Point* p) {
    p->x += 1;       // pointer member access (->)
    (*p).y += 1;     // dereference + dot member access
}

// --- Function with array parameter and for loop ---
int sum_array(int arr[], int size) {
    int sum = 0;
    for (int i = 0; i < size; i = i + 1) {
        sum = sum + arr[i];
    }
    return sum;
}

// --- Function with while loop and break/continue ---
int count_even(int arr[], int size) {
    int count = 0;
    int i = 0;
    while (i < size) {
        if (arr[i] == 0) {
            i = i + 1;
            continue;   // skip zero
        }
        if (arr[i] % 2 == 0) {
            count = count + 1;
        }
        i = i + 1;
    }
    return count;
}

// --- Function using multiple parameters and logical operators ---
int is_in_range(int value, int low, int high) {
    return (value >= low) && (value <= high);
}

// --- Function returning pointer to struct (malloc usage) ---
// struct Point* create_point(int x, int y) {
//     struct Point* p = (struct Point*)malloc(sizeof(struct Point));
//     p->x = x;
//     p->y = y;
//     return p;
// }

// --- Function with recursion and binary operations ---
int power(int base, int exp) {
    if (exp == 0) {
        return 1;
    }
    return base * power(base, exp - 1);
}

// --- Function demonstrating all expression types ---
int expression_demo() {
    int a = 10;
    int b = 20;
    int c;

    // Arithmetic
    c = a + b - 3 * 4 / 2;

    // Relational
    int flag = (a < b) && (b > 15) || (a == 10);

    // Assignment operators
    a += 5;
    b -= 2;
    c *= 2;
    c /= 3;

    // Unary operators
    int d = -a;
    int e = +b;
    int f = !flag;
    int g = *(&a);   // pointer dereference
    int h = ++a;     // pre-increment
    int i = b--;     // post-decrement

    // Array access
    int arr[5] = {1, 2, 3, 4, 5};
    int first = arr[0];
    int last = arr[4];

    // Function calls
    int sum = add(a, b);
    int fact = factorial(5);

    // Struct member access (dot)
    struct Point p1 = {1, 2};
    int px = p1.x;
    int py = p1.y;

    // Pointer to struct and member access (->)
    // struct Point* p2 = create_point(3, 4);
    // int px2 = p2->x;
    // int py2 = p2->y;

    // Multiple variable declaration with initialization
    int x1 = 0, x2 = 1, x3 = 2;

    // Array initialization with braces
    // int matrix[2][2] = {{1, 2}, {3, 4}};

    // Return a dummy value to show we executed
    return px + py +  sum + fact;
}

// --- Function using for loop with break ---
int find_first(int arr[], int size, int target) {
    for (int i = 0; i < size; i = i + 1) {
        if (arr[i] == target) {
            return i;
        }
    }
    return -1;
}

// --- Function with void return and no parameters ---
void do_nothing() {
    // empty body
}

// --- Main function ---
int main() {
    // Variable declarations with initialization
    int x = 10;
    int y = 20;
    int z = 30;

    // Struct declaration and initialization
    struct Point p = {5, 7};
    // struct Point* pp = create_point(8, 9);

    // Function calls
    int result = add(x, y);
    int fact = factorial(5);
    // int even_count = count_even((int[]){1, 2, 3, 4, 5, 6}, 6);
    // int idx = find_first((int[]){1, 2, 3, 4, 5}, 5, 3);

    // Conditional statements
    if (result > 0) {
        do_nothing();   // then branch
    } else {
        do_nothing();   // else branch
    }

    // While loop
    int i = 0;
    while (i < 10) {
        i = i + 1;
        if (i == 5) {
            continue;
        }
        do_nothing();   // dummy operation
    }

    // For loop with break
    for (int j = 0; j < 10; j = j + 1) {
        if (j == 7) {
            break;
        }
        do_nothing();
    }

    // Return statement
    return 0;
}

// --- Function definition after main (prototype already declared) ---
int add(int a, int b) {
    return a + b;
}

// --- Function definition using struct parameter ---
void print_point(struct Point p) {
    // No printf, just a dummy statement to avoid unused warning
    int dummy = p.x + p.y;
}