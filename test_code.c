// ========================================================
// Comprehensive Valid Mini-C Test Code
// Testing Lexer, Parser, Semantic Analysis, and Type Checker
// ========================================================

// 1. Struct Declarations (تست تعریف استراکت و نوع‌دهی)
struct Point {
    int x;
    int y;
    float z;
};

// تست استراکت تو در تو و پوینتر به استراکت
struct Node {
    struct Point data;
    struct Node* next;
};

// 2. Global Variables (تست متغیرهای سراسری و مقداردهی اولیه)
int global_count = 0;
float PI = 3.14159f;
char NEWLINE = '\n';
char* greeting = "Hello, Mini-C Compiler!";

// 3. Function Prototypes (تست اعلام توابع - Prototype)
int factorial(int n);
struct Point create_point(int x, int y, float z);

// 4. Recursive Function Definition (تست توابع بازگشتی و دستورات شرطی)
int factorial(int n) {
    if (n <= 1) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

// 5. Array Parameters & Loops (تست پارامترهای آرایه، حلقه‌ها، Break و Continue)
void process_array(int arr[], int size) {
    int i;
    for (i = 0; i < size; i++) {
        if (arr[i] % 2 == 0) {
            arr[i] += 10;
            continue;
        }
        
        if (arr[i] > 100) {
            break;
        }
        
        arr[i] *= 2;
    }
}

// 6. Function returning a Struct (تست بازگرداندن استراکت از تابع)
struct Point create_point(int x, int y, float z) {
    struct Point p;
    p.x = x;
    p.y = y;
    p.z = z;
    return p;
}

// 7. Main Function (تست تمامی ترکیب‌ها در کنار هم)
int main() {
    // الف) متغیرهای محلی و لیترال‌های مختلف
    int a = 5,b = 10;
    float result = 0.0f;
    double d_val = 2.718;
    char c = 'A';
    
    // ب) پوینترها و عملگرهای گرفتن آدرس
    int* ptr_a = &a;
    int** double_ptr = &ptr_a;
    
    // ج) آرایه‌ها و لیست‌های مقداردهی (Initializer Lists)
    int numbers[5] = {1, 2, 3, 4, 5};
    char* msg = greeting;
    
    // د) وهله‌سازی از استراکت‌ها
    struct Point p1 = {0, 0, 0.0f};
    struct Point p2;
    struct Node n1;
    struct Node n2;
    
    // ه) عملگرهای یگانی (Unary) و Postfix
    global_count++;
    --b;
    
    // و) عبارات منطقی، رابطه‌ای و ریاضی
    if (*ptr_a == 5 && b != 0 || !0) {
        // تبدیل نوع ضمنی (int به float) در اینجا ارزیابی می‌شود
        result = (a + b) / 2.0f; 
    }
    
    // ز) فراخوانی تابع و دسترسی به فیلدهای استراکت
    p2 = create_point(10, 20, PI);
    n1.data = p2;
    
    // ح) انتساب پوینترها (ایجاد لیست پیوندی حلقوی برای تست نوع پوینترها)
    n2.data = p1;
    n1.next = &n2;
    n2.next = &n1; 
    
    // ط) دی‌رفرنس کردن پوینتر چندگانه و ارسال آرایه به تابع
    **double_ptr = factorial(5);
    process_array(numbers, 5);
    
    // ی) حلقه While و جلوگیری از Warning متغیرهای استفاده نشده
    while (global_count < 10) {
        global_count += 2;
    }
    
    if (NEWLINE == '\n') {
        c = 'B';
        d_val += 1.0;
        msg = "Hi!";
    }
    
    return 0;
}