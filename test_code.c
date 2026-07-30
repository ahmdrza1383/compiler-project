void swap(int** ptr1, int** ptr2) {
    int* temp = *ptr1;
    *ptr1 = *ptr2;
    *ptr2 = temp;
}

int main() {
    int arr[5] = {1, 2, 3, 4, 5};
    int* p = &arr[0];
    int** pp = &p;
    
    // Testing pointer arithmetic and dereferencing vs multiplication
    *(p + 2) = **pp * 10;
    
    // Incrementing pointer
    p++;
    
    // Bitwise AND vs Address-of (Contextually different, lexically identical)
    int mask = 0x0F & 0xFF;
    swap(&p, pp);
    
    return 0;
}