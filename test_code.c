int main() {
    int x = 42;
    int *ptr;
    ptr = &x;
    
    *ptr = *ptr + 8;
    
    return x;
}