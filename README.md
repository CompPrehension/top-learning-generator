# ToP: "Training of Programmers" or "Tons of Problems" 

Associated publication: _Learning Problem Generator for Introductory Programming Courses_ (expected to be published)

ToP, a learning problem generator, is intended to generate learning questions (or problems) for learning the basics of programming from open source code.  
The types of learning problems currently supported (multi-step problems only, so far) are: 
 - expression evaluation order, which teaches precedence and associativity; 
 - and program tracing, which teaches control flow statements and basic concepts of repetition and choice.
 
Multiple problems can be created from the same piece of code by changing concrete values of control conditions and thus possibly changing the solution path.

### Languages and Technologies 

- Java, Python, C++
- Apache Jena, RDF
- Clang


### Installation steps
- Download the clang-cl module for Visual Studio 2019
- Install cmake
- Download llvm sources
- Go to the sources folder and prepare them for compilation via cmake
```
cmake -G "Visual Studio 16 2019" -S llvm -B _build_llvm ^
        -T "ClangCL" ^
        -DLIBCXX_ENABLE_SHARED=YES ^
        -DLLVM_ENABLE_PROJECTS=clang ^
        -DLIBCXX_ENABLE_STATIC=NO ^
        -DLIBCXX_ENABLE_EXPERIMENTAL_LIBRARY=NO
```
- Go to the _build_llvm directory and open LLVM.sln
- Run the build of clang and clang_tools projects
- Change the paths for the compiled libraries in the project settings



### Получение репозитория с генератором вопросов

Склонировать с подмодулями:

```
git clone  --recurse-submodules https://github.com/CompPrehension/top-learning-generator.git
```

Установить зависимости:
```
pip install -r requirements.txt
pip install -r c_owl/requirements.txt
```


