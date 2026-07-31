// Complex integration test for C-like parser

struct Vector {
    int x;
    int y;
    int z;
};

// Recursive function to test param lists and block scoping
int factorial(int n) {
    if (n <= 1) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

// Function with pointers and multiple parameters
void update_vector(struct Vector *v, int scale) {
    if (scale > 0) {
        v.x = v.x * scale;
        v.y = v.y * scale;
        v.z = v.z * scale;
    }
}

int main() {
    // Array declaration with initializer (your recent fix)
    int weights[4] = {2, 4, 6, 8};
    
    // Complex pointer declaration and assignment
    int *weight_ptr = &weights[2];
    
    // Struct declaration (assuming your grammar supports it like this)
    struct Vector v1 = {10, 20, 30};
    struct Vector *v_ptr = &v1;
    
    // Variables for logic flow
    float threshold = 15.5f;
    char mode = 'A';
    int status = 0;
    
    // Complex condition combining logical and relational operators
    if (*weight_ptr >= 5 && threshold < 20.0f) {
        status = factorial(*weight_ptr);
        update_vector(v_ptr, status);
    } else {
        status = -1;
    }
    
    // Deep expression evaluation
    int final_result = (status * weights[0]) + (v1.x / 2) - 100;
    
    // Test panic mode with intentional trailing garbage
    float bad_syntax = 1.0 + / ;
    
    return final_result;
}