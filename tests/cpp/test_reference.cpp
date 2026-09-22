#include "../../cpp/ito_reference/journal_file.hpp"

#include <cassert>
#include <cstdio>
#include <fstream>
#include <string>

int main() {
    const std::string path = "/tmp/ito_reference_journal_test.jsonl";
    std::remove(path.c_str());
    {
        ito::reference::JournalFile journal(path);
        assert(journal.healthy());
        assert(journal.last_sequence() == 0);
        assert(journal.file_size() > 0);
    }
    {
        ito::reference::JournalFile journal(path);
        assert(journal.healthy());
        assert(journal.last_sequence() == 0);
    }
    std::remove(path.c_str());
    return 0;
}
