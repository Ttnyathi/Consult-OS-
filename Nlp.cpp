#include <iostream>
#include <fstream>

#include "Nlp.h"

namespace NLP {

bool sameWord(const char* a, const char* b){
    int i = 0;

    while (a[i] != '\0' && b[i] != '\0') {
        if (a[i] != b[i]) {
            return false;
        }
        i++;
    }

    return a[i] == '\0' && b[i] == '\0';
}

int wordLength(const char* word){
    int count = 0;

    while (word[count] != '\0') {
        count++;
    }

    return count;
}

void copyWord(char* dest, const char* src){
    int i = 0;

    while (src[i] != '\0') {
        dest[i] = src[i];
        i++;
    }

    dest[i] = '\0';
}

void makeLower(char* word){
    int i = 0;

    while (word[i] != '\0') {
        if (word[i] >= 'A' && word[i] <= 'Z') {
            word[i] = word[i] + 32;
        }
        i++;
    }
}

int countTokens(const char* filename){
    if (filename == NULL) {
        return 0;
    }

    std::ifstream file(filename);

    if (!file.is_open()) {
        return 0;
    }

    char word[1000];
    int count = 0;

    while (file >> word) {
        count++;
    }

    return count;
}

int countSentences(const char* filename){
    if (filename == NULL) {
        return 0;
    }

    std::ifstream file(filename);

    if (!file.is_open()) {
        return 0;
    }

    char c;
    int count = 0;

    while (file.get(c)) {
        if (c == '.' || c == '!' || c == '?') {
            count++;

            while (file.peek() == '.' || file.peek() == '!' || file.peek() == '?') {
                file.get(c);
            }
        }
    }

    return count;
}

void sanitise(const char* src, char* dest){
    if (src == NULL || dest == NULL) {
        return;
    }

    int i = 0;
    int j = 0;

    while (src[i] != '\0') {
        if ((src[i] >= 'A' && src[i] <= 'Z') ||
            (src[i] >= 'a' && src[i] <= 'z') ||
            (src[i] >= '0' && src[i] <= '9')) {

            dest[j] = src[i];
            j++;
        }

        i++;
    }

    dest[j] = '\0';
}

void replaceAndTransfer(const char* srcname, const char* destname, const char* mapname){
    if (srcname == NULL || destname == NULL || mapname == NULL) {
        return;
    }

    std::ifstream src(srcname);
    std::ifstream map(mapname);

    if (!src.is_open() || !map.is_open()) {
        return;
    }

    std::ofstream dest(destname);

    if (!dest.is_open()) {
        return;
    }

    char mapWords[100][1000];
    char replacements[100][1000];
    int count = 0;

    while (count < 100 && map >> mapWords[count] >> replacements[count]) {
        count++;
    }

    char word[1000];

    while (src >> word) {
        bool replaced = false;

        for (int i = 0; i < count && !replaced; i++) {
            if (sameWord(word, mapWords[i])) {
                dest << replacements[i] << " ";
                replaced = true;
            }
        }

        if (!replaced) {
            dest << word << " ";
        }
    }
}

bool isStopWord(const char* word){
    if (word == NULL) {
        return false;
    }

    char temp[1000];
    copyWord(temp, word);
    makeLower(temp);

    if (sameWord(temp, "the")) {
        return true;
    }
    if (sameWord(temp, "and")) {
        return true;
    }
    if (sameWord(temp, "is")) {
        return true;
    }
    if (sameWord(temp, "of")) {
        return true;
    }
    if (sameWord(temp, "to")) {
        return true;
    }
    if (sameWord(temp, "a")) {
        return true;
    }

    return false;
}

void extractVocabulary(const char* srcname, const char* destname){
    if (srcname == NULL || destname == NULL) {
        return;
    }

    std::ifstream src(srcname);

    if (!src.is_open()) {
        return;
    }

    std::ofstream dest(destname);

    if (!dest.is_open()) {
        return;
    }

    char vocab[1000][1000];
    int count = 0;
    char word[1000];

    while (src >> word) {
        char clean[1000];

        sanitise(word, clean);
        makeLower(clean);

        if (wordLength(clean) >= 4 && !isStopWord(clean)) {
            bool exists = false;

            for (int i = 0; i < count; i++) {
                if (sameWord(vocab[i], clean)) {
                    exists = true;
                }
            }

            if (!exists && count < 1000) {
                copyWord(vocab[count], clean);
                count++;

                dest << clean << '\n';
            }
        }
    }
}

void charFrequency(const char* filename){
    if (filename == NULL) {
        return;
    }

    std::ifstream file(filename);

    if (!file.is_open()) {
        return;
    }

    int freq[26];

    for (int i = 0; i < 26; i++) {
        freq[i] = 0;
    }

    char c;

    while (file.get(c)) {
        if ((c >= 'A' && c <= 'Z') ||
            (c >= 'a' && c <= 'z')) {

            if (c >= 'A' && c <= 'Z') {
                c = c + 32;
            }

            freq[c - 'a']++;
        }
    }

    file.close();

    std::ofstream out(filename, std::ios::app);

    if (!out.is_open()) {
        return;
    }

    out << '\n';
    out << "Character Frequencies:" << '\n';

    for (int i = 0; i < 26; i++) {
        out << char('A' + i) << ": " << freq[i] << '\n';
    }
}

void generateNGrams(const char* filename, int n){
    if (filename == NULL) {
        return;
    }

    if (n <= 0 || n > 10) {
        return;
    }

    std::ifstream file(filename);

    if (!file.is_open()) {
        return;
    }

    char words[1000][1000];
    int count = 0;
    char word[1000];

    while (count < 1000 && file >> word) {
        char clean[1000];

        sanitise(word, clean);

        if (clean[0] != '\0') {
            copyWord(words[count], clean);
            count++;
        }
    }

    if (count < n) {
        return;
    }

    const char* name = "";

    if (n == 1) {
        name = "Unigram";
    }
    else if (n == 2) {
        name = "Bigram";
    }
    else if (n == 3) {
        name = "Trigram";
    }
    else if (n == 4) {
        name = "4-gram";
    }
    else if (n == 5) {
        name = "5-gram";
    }
    else if (n == 6) {
        name = "6-gram";
    }
    else if (n == 7) {
        name = "7-gram";
    }
    else if (n == 8) {
        name = "8-gram";
    }
    else if (n == 9) {
        name = "9-gram";
    }
    else if (n == 10) {
        name = "10-gram";
    }

    for (int i = 0; i <= count - n; i++) {
        std::cout << name << ": [";

        for (int j = 0; j < n; j++) {
            std::cout << words[i + j];

            if (j != n - 1) {
                std::cout << " ";
            }
        }

        std::cout << "]" << std::endl;
    }
}

bool containsKeyword(const char* filename, const char* keyword){
    if (filename == NULL || keyword == NULL) {
        return false;
    }

    std::ifstream file(filename);

    if (!file.is_open()) {
        return false;
    }

    char word[1000];

    while (file >> word) {
        if (sameWord(word, keyword)) {
            return true;
        }
    }

    return false;
}

} // namespace NLP
