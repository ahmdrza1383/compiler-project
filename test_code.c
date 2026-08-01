struct Point {
    int x;
    int y;
};

int main() {
    struct Point p = {10, 20};
    int sum = p.x + p.y;
    return sum;
}