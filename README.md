# Инструкция по установке
- Загрузить модуль clang-cl для Visual Studio 2019
- Установить cmake
- Скачать исходники llvm
- Зайти в папку исходников и подготовить их к компиляции через cmake
```
cmake -G "Visual Studio 16 2019" -S llvm -B _build_llvm ^
        -T "ClangCL"                                  ^
        -DLIBCXX_ENABLE_SHARED=YES                    ^
        -DLLVM_ENABLE_PROJECTS=clang                  ^
        -DLIBCXX_ENABLE_STATIC=NO                     ^
        -DLIBCXX_ENABLE_EXPERIMENTAL_LIBRARY=NO
```
- Перейти в директорию _build_llvm и открыть LLVM.sln
- Запустить билд проектов clang и clang_tools
- Поменять в настройках проекта пути под скомпилированные библиотеки
