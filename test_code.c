struct Node {
    int value;
    struct Node* next;
};

int process_node(struct Node* n, int threshold) {
    if (n == 0) {
        return 0;
        int dead_var = 99; // تست کد مرده
    }
    
    if (n->value > threshold) {
        return 1;
    } else {
        return -1;
    }
}

int complex_algorithm(int max_iters, struct Node* head) {
    int i = 0;
    int active_nodes = 0;

    while (i < max_iters) {
        if (head == 0) {
            break; 
        }
        
        int status = process_node(head, 50);
        
        if (status == 1) {
            active_nodes++;
        } else {
            if (status == -1) {
                head = head->next;
                continue; 
            }
        }
        
        head = head->next;
        i++;
        
        for (int j = 0; j < 5; j++) {
            if (active_nodes > 100) {
                return active_nodes; 
            }
        }
    }
    
    return active_nodes;
}

int main() {
    struct Node n1 = {10, 0};
    struct Node n2 = {60, &n1};
    
    int result = complex_algorithm(10, &n2);
    return 0;
}