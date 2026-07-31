// Test code for while loop and 1D array

int main() {

    int arr[5];

    int i = 0;

    int sum = 0;

   

    while (i < 5) {

        arr[i] = i * 2;

        sum = sum + arr[i];

        i = i + 1;

    }

   

    return sum;

}